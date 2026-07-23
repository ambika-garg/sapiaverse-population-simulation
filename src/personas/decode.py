"""Translate PUMS numeric codes into human-readable text."""

import pandas as pd


def _lookup(code: object, labels: dict[str, str]) -> str:
    """Resolve one code against a label dictionary, tolerating zero-padding."""
    if pd.isna(code):
        return "Not reported"

    raw = str(code).strip()
    for candidate in (raw, raw.lstrip("0") or "0", raw.zfill(2), raw.zfill(3), raw.zfill(4)):
        if candidate in labels:
            return labels[candidate]
    return "Not reported"


def decode_frame(frame: pd.DataFrame, label_sets: dict[str, dict[str, str]]) -> pd.DataFrame:
    """Add a readable `<VAR>_label` column for every coded variable."""
    decoded = frame.copy()
    for variable, labels in label_sets.items():
        if variable in decoded.columns:
            decoded[f"{variable}_label"] = decoded[variable].map(
                lambda code, lbl=labels: _lookup(code, lbl)
            )
    return decoded
