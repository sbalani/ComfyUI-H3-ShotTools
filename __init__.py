"""Timing and prompt checks for Fantastic H3, with a visible seconds control."""
import math
import re

CANVASES = {
    'Draft landscape 672x384': (672, 384),
    'Native landscape 1344x768': (1344, 768),
    'Draft portrait 384x672': (384, 672),
    'Native portrait 768x1344': (768, 1344),
    'Native square 992x992': (992, 992),
    'Native scope 1536x640': (1536, 640),
}


def plan_seconds(seconds, text):
    seconds = float(seconds)
    if not math.isfinite(seconds) or not 5 <= seconds <= 15:
        raise ValueError('Use 5–15 seconds per H3 clip. For longer sequences, render separate clips and concatenate them.')
    export_frames = round(seconds * 24)
    export_seconds = export_frames / 24
    frames = max(124, 5 + 17 * math.ceil((export_frames - 5) / 17))
    detail = text.partition('detailed_description:')[2].split('overall_soundscape:')[0]
    if not detail.strip():
        raise ValueError('Use Fantastic REF mode with a detailed_description section.')
    shots = list(re.finditer(r'\[Shot\s+(\d+)\]', detail, re.I))
    if not shots or [int(m[1]) for m in shots] != list(range(1, len(shots)+1)):
        raise ValueError('Start the shot description with [Shot 1]; number each later shot once, in order.')
    cuts = []
    for i, shot in enumerate(shots):
        end = shots[i+1].start() if i+1 < len(shots) else len(detail)
        section = detail[shot.end():end].lstrip()
        cut = re.match(r'At\s+(\d{2}):([0-5]\d)\.(\d{3})\b', section, re.I)
        if i == 0:
            if cut: raise ValueError('Do not timestamp [Shot 1]. Later shots use At MM:SS.mmm.')
            continue
        if not cut: raise ValueError(f'[Shot {i+1}] needs At MM:SS.mmm immediately after its marker.')
        t = int(cut[1])*60+int(cut[2])+int(cut[3])/1000
        if not 0 < t < export_seconds or (cuts and t <= cuts[-1]):
            raise ValueError('Cut times must increase and fall inside the exported clip duration.')
        cuts.append(t)
    for section in ['subject_definitions:', 'summary:', 'retention_analysis:']:
        if section not in text: raise ValueError(f'Missing REF prompt section: {section}')
    return frames, export_seconds, cuts


class FantasticH3ShotPlan:
    CATEGORY = 'video/H3 Shot Tools'
    DESCRIPTION = ('Set seconds here. Checks the Fantastic REF prompt and cut times, rounds generation '
                   'up to the H3 frame grid, and supplies a frame-accurate export trim.')
    RETURN_TYPES = ('STRING', 'INT', 'FLOAT', 'INT', 'INT', 'INT', 'FLOAT', 'STRING')
    RETURN_NAMES = ('checked_prompt', 'generation_frames', 'fps', 'width', 'height', 'steps', 'export_seconds', 'timing_report')
    FUNCTION = 'build'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'prompt_text': ('STRING', {'forceInput': True}),
            'seconds': ('FLOAT', {'default': 5.0, 'min': 5.0, 'max': 15.0, 'step': 0.1}),
            'canvas': (list(CANVASES), {'default': 'Draft landscape 672x384'}),
            'steps': ('INT', {'default': 20, 'min': 12, 'max': 50, 'step': 1}),
        }}

    def build(self, prompt_text, seconds, canvas, steps):
        frames, export_seconds, cuts = plan_seconds(seconds, prompt_text)
        width, height = CANVASES[canvas]
        report = (f'{seconds:g} s requested → {frames} generated frames '
                  f'({frames/24:.3f} s) → {round(export_seconds*24)} exported frames ({export_seconds:.3f} s). '
                  f'{width}×{height}, 24 fps, {steps} steps. '
                  f'{len(cuts)+1} prompted shot(s); cuts at {cuts or "none"}. '
                  'Prompted cuts are approximate; separate clips give exact edit boundaries.')
        return {'ui': {'text': [report]}, 'result': (prompt_text, frames, 24.0, width, height, steps, export_seconds, report)}

NODE_CLASS_MAPPINGS = {'FantasticH3ShotPlan': FantasticH3ShotPlan}
NODE_DISPLAY_NAME_MAPPINGS = {'FantasticH3ShotPlan': 'Fantastic H3 Shot Plan · Seconds to Frames'}
