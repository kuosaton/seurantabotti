"""
Committee monitoring client – Sprint 2.

Pipeline (to be implemented):
  1. GET committee main page HTML (~3 MB, server-rendered SPA)
  2. Regex-extract VS (viikkosuunnitelma) and TaVE/MmVE/YmVE (esityslista) items
     from the embedded JavaScript object literals (not valid JSON – keys unquoted)
  3. For each new esityslista: fetch full XML from VaskiData by exact Eduskuntatunnus
  4. Parse matter references (HE/LA/etc.) and titles from XmlData column
  5. Score each matter via llm_scorer

Key facts verified 2026-04-22:
- Embedded JS field names: edktunnus, eduskuntatunnus, asiakirjatyyppikoodi,
  nimeketeksti, laadintapvm, viimeisinJulkaisuajankohta
- Document type codes: VS, KS, TaVE/MmVE/YmVE, TaVP/MmVP/YmVP, TaVM/MmVM/YmVM
- VaskiData column is "Eduskuntatunnus" (not "Pitkätunnus")
- VaskiData requires exact full document code, e.g. "TaVE 37/2026 vp"
- VaskiData base URL: https://avoindata.eduskunta.fi/api/v1
"""

raise NotImplementedError("eduskunta client is scheduled for Sprint 2")
