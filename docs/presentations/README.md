# GIE Presentations

| Deck | Purpose |
|------|---------|
| [GIE_Overview_Architecture.pptx](GIE_Overview_Architecture.pptx) | Executive / architecture overview |
| [GIE_Management_Orchestration_Layer.pptx](GIE_Management_Orchestration_Layer.pptx) | Management review — guardrail/policy orchestration + leverage layers |
| [GIE_Management_Orchestration_Layer.html](GIE_Management_Orchestration_Layer.html) | Same management deck as browser slides |
| [GIE_Technical_Deep_Dive.pptx](GIE_Technical_Deep_Dive.pptx) | Detailed technical discussion & demo |
| [GIE_Technical_Deep_Dive.html](GIE_Technical_Deep_Dive.html) | Same deck as browser slides (always renders) |

**Open the `.pptx` in Microsoft PowerPoint or Keynote** (download the file first). GitHub / some IDE previews show PPTX as blank even when the file has content.

## Regenerate PPTX

```bash
python3 docs/scripts/generate_gie_technical_pptx.py
python3 docs/scripts/generate_gie_management_pptx.py
```

Requires `python-pptx` and `lxml`.
