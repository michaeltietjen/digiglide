# Installing DigiGlide without building it

Read the recovery warning in the [main README](../README.md) first.

```
python3 digiglide_patch.py /path/to/Digitone_II_OS1.12.syx
```

It writes `DN2_1.12_DIGIGLIDE_35.syx` beside your file, and only if the result is the tested image byte for byte.
It needs Python 3.10 or newer and nothing else.

| File | What |
| --- | --- |
| `digiglide_patch.py` | The patcher |
| `DigiGlide_35.dgpatch` | The patch: DigiGlide's compiled code and where it goes. No Elektron firmware |
| `make_patch.py` | Makes the patch from a build (for the developer) |
| `vendor/dnfw/` | dnfw's container code, unchanged (AGPL-3.0-or-later) |
| `vendor/dnfw_csrc/` | Source of dnfw's loader, which every image contains |

Licences: [NOTICE](../NOTICE).
