"""Exportação de relatórios para Excel e CSV."""
import io

import pandas as pd


def para_excel(folhas: dict) -> bytes:
  """folhas = {"Nome da folha": DataFrame}. Devolve o ficheiro .xlsx em bytes."""
  buf = io.BytesIO()
  with pd.ExcelWriter(buf, engine="openpyxl") as xl:
    for nome, df in folhas.items():
      df.to_excel(xl, sheet_name=nome[:31], index=False)
      ws = xl.sheets[nome[:31]]
      for i, col in enumerate(df.columns, start=1):
        largura = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)]) + 2
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(largura, 50)
      ws.freeze_panes = "A2"
  return buf.getvalue()


def para_csv(df: pd.DataFrame) -> bytes:
  return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")  # abre bem no Excel pt
