from typing import Dict, List

from controllers.cuotas.VariosCuotasGenerales import extract_cronograma_cuotas_from_text


def extract_cronograma_cuotas_rimac(text: str | None, moneda_default: str | None = None) -> List[Dict[str, object]]:
    return extract_cronograma_cuotas_from_text(text, moneda_default)
