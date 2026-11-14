import pytest
import pandas as pd
from pathlib import Path
from nazaret_quant.data import validate

def test_validate_edge_cases_and_rejections(tmp_path):
    # Constrói um DataFrame válido mínimo para testar rejeições específicas de qualidade
    base = pd.DataFrame({
        "timestamp": ["2026-06-01T10:00:00Z", "2026-06-01T10:05:00Z"],
        "bar_open": ["2026-06-01T09:55:00Z", "2026-06-01T10:00:00Z"],
        "symbol": ["TEST3", "TEST3"],
        "open": [10.0, 10.5],
        "high": [10.6, 11.0],
        "low": [9.8, 10.4],
        "close": [10.5, 10.8],
        "volume": [1000.0, 1500.0],
        "session": ["2026-06-01", "2026-06-01"]
    })
    
    # 1. Validação bem-sucedida padrão
    validated, info = validate(base)
    assert info["rows"] == 2
    
    # 2. Teste de timestamp sem fuso horário (ingênuo)
    naive = base.copy()
    naive.loc[0, "timestamp"] = "2026-06-01T10:00:00"
    with pytest.raises(ValueError, match="Timezone explícito obrigatório"):
        validate(naive)
        
    # 3. Teste de sessão divergente da data local da barra
    wrong_session = base.copy()
    wrong_session.loc[0, "session"] = "2025-01-01"
    with pytest.raises(ValueError, match="Sessão deve coincidir com data local da barra"):
        validate(wrong_session)
        
    # 4. Teste de barras sobrepostas (bar_open anterior ao timestamp anterior)
    overlap = base.copy()
    overlap.loc[1, "bar_open"] = "2026-06-01T09:50:00Z"
    with pytest.raises(ValueError, match="Barras sobrepostas"):
        validate(overlap)
