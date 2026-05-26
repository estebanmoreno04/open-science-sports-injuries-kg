"""
abstract_similarity.py
----------------------
Script para calcular la similitud semántica entre abstracts de papers científicos.
Genera embeddings con sentence-transformers y calcula la matriz de similitud coseno.

Forma parte del workflow de construcción del Knowledge Graph de lesiones deportivas.

Uso:
    python scripts/abstract_similarity.py

Salidas (en OUTPUT_DIR):
    - similarity_matrix_<modelo>.csv   → Matriz cuadrada de similitud
    - top3_similar_<modelo>.csv        → Top-K papers más similares por paper
    - run_info_<modelo>.txt            → Log de la ejecución
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# =============================================================================
# CONFIGURACIÓN PRINCIPAL
# =============================================================================

# Ruta al CSV de entrada (con columnas: paper_id, title, abstract)
INPUT_CSV = Path("data/metadata/papers.csv")

# Directorio de salida (se crea automáticamente si no existe)
OUTPUT_DIR = Path("results/similarity")

# Número de papers similares a recuperar por cada paper (excluye autocomparación)
TOP_K = 3

# ---------------------------------------------------------------------------
# SELECCIÓN DE MODELO — comenta/descomenta para cambiar de modelo
# ---------------------------------------------------------------------------
# MODEL_NAME = "intfloat/e5-small-v2"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# ---------------------------------------------------------------------------

# Separador del CSV de entrada (ajustar si el fichero usa ',' u otro)
CSV_SEPARATOR = ";"

# =============================================================================
# FUNCIONES
# =============================================================================


def load_data(input_path: Path) -> pd.DataFrame:
    """
    Carga el CSV de entrada y realiza una limpieza mínima:
      - Elimina filas con abstract vacío o nulo.
      - Elimina duplicados por paper_id.
      - Aplica strip() a los campos de texto relevantes.

    Lanza un ValueError si faltan columnas obligatorias.
    """
    required_columns = {"paper_id", "title", "abstract"}

    print(f"[INFO] Cargando datos desde: {input_path}")
    df = pd.read_csv(input_path, sep=CSV_SEPARATOR, dtype=str)

    # Comprobación de columnas obligatorias
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"El CSV de entrada no contiene las columnas obligatorias: {missing}\n"
            f"Columnas encontradas: {list(df.columns)}"
        )

    n_raw = len(df)

    # Limpieza de espacios en campos clave
    df["paper_id"] = df["paper_id"].str.strip()
    df["title"] = df["title"].str.strip()
    df["abstract"] = df["abstract"].str.strip()

    # Eliminar filas con abstract vacío o nulo
    df = df[df["abstract"].notna() & (df["abstract"] != "")]
    n_after_abstract = len(df)
    dropped_abstract = n_raw - n_after_abstract
    if dropped_abstract > 0:
        print(f"[WARN] Se eliminaron {dropped_abstract} fila(s) con abstract vacío o nulo.")

    # Eliminar duplicados por paper_id (conserva la primera aparición)
    df = df.drop_duplicates(subset="paper_id", keep="first")
    n_after_dedup = len(df)
    dropped_dedup = n_after_abstract - n_after_dedup
    if dropped_dedup > 0:
        print(f"[WARN] Se eliminaron {dropped_dedup} fila(s) duplicadas por paper_id.")

    df = df.reset_index(drop=True)
    print(f"[INFO] Papers válidos para procesar: {n_after_dedup}")
    return df


def prepare_texts(df: pd.DataFrame, model_name: str) -> list[str]:
    """
    Prepara los textos de los abstracts para la generación de embeddings.

    Para modelos de la familia E5 (intfloat/e5-*), la convención recomendada
    es anteponer el prefijo "passage: " a los textos que se van a indexar/comparar
    entre sí. Dado que todos los abstracts tienen el mismo rol (compararlos entre
    sí), se usa "passage: " de forma consistente para todos ellos.

    Para otros modelos (ej. all-MiniLM-L6-v2), no se añade ningún prefijo.
    """
    is_e5 = "e5" in model_name.lower() and "intfloat" in model_name.lower()

    if is_e5:
        prefix = "passage: "
        print(f"[INFO] Modelo E5 detectado -> aplicando prefijo '{prefix}' a todos los abstracts.")
        texts = [prefix + abstract for abstract in df["abstract"].tolist()]
    else:
        print(f"[INFO] Modelo estándar -> sin prefijo en los abstracts.")
        texts = df["abstract"].tolist()

    return texts


def generate_embeddings(texts: list[str], model_name: str) -> np.ndarray:
    """
    Carga el modelo sentence-transformer e genera los embeddings de los textos.

    Los embeddings se normalizan a norma unitaria (L2) antes de devolverlos,
    lo que hace que el producto escalar sea equivalente a la similitud coseno
    y mejora la estabilidad numérica del cálculo posterior.
    """
    print(f"[INFO] Cargando modelo: {model_name} ...")
    model = SentenceTransformer(model_name)

    print(f"[INFO] Generando embeddings para {len(texts)} abstracts ...")
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,   # normalización L2 incorporada
        convert_to_numpy=True,
    )

    print(f"[INFO] Embeddings generados. Shape: {embeddings.shape}")
    return embeddings


def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Calcula la matriz de similitud coseno entre todos los pares de embeddings.
    Devuelve una matriz cuadrada (n_papers × n_papers).

    Como los embeddings ya están normalizados (norma L2 = 1), esta operación
    es equivalente al producto escalar y produce valores en [-1, 1].
    """
    print("[INFO] Calculando matriz de similitud coseno ...")
    sim_matrix = cosine_similarity(embeddings)
    return sim_matrix


def get_top_k_similar(
    df: pd.DataFrame,
    sim_matrix: np.ndarray,
    top_k: int,
) -> pd.DataFrame:
    """
    Para cada paper, obtiene los top_k papers más similares,
    excluyendo la autocomparación (diagonal de la matriz).

    Devuelve un DataFrame con las columnas:
        source_paper_id, source_title, rank,
        similar_paper_id, similar_title, similarity_score
    """
    print(f"[INFO] Extrayendo top-{top_k} papers similares por paper ...")
    rows = []
    n = len(df)

    for i in range(n):
        # Puntuaciones del paper i con todos los demás
        scores = sim_matrix[i].copy()

        # Excluir la autocomparación poniendo la diagonal a -inf
        scores[i] = -np.inf

        # Índices de los top_k más similares (orden descendente)
        top_indices = np.argsort(scores)[::-1][:top_k]

        for rank, j in enumerate(top_indices, start=1):
            rows.append(
                {
                    "source_paper_id": df.loc[i, "paper_id"],
                    "source_title": df.loc[i, "title"],
                    "rank": rank,
                    "similar_paper_id": df.loc[j, "paper_id"],
                    "similar_title": df.loc[j, "title"],
                    "similarity_score": round(float(scores[j]), 6),
                }
            )

    return pd.DataFrame(rows)


def sanitize_model_name(model_name: str) -> str:
    """
    Convierte el nombre del modelo en una cadena válida para nombres de fichero,
    reemplazando '/' y otros caracteres problemáticos por '_'.
    """
    return model_name.replace("/", "_").replace("-", "_").replace(".", "_")


def save_outputs(
    df: pd.DataFrame,
    sim_matrix: np.ndarray,
    top_k_df: pd.DataFrame,
    input_path: Path,
    output_dir: Path,
    model_name: str,
    top_k: int,
    n_dropped_abstract: int,
    n_dropped_dedup: int,
) -> None:
    """
    Guarda en disco todos los ficheros de salida del script:
      1. similarity_matrix_<modelo>.csv  → matriz cuadrada de similitud
      2. top3_similar_<modelo>.csv       → tabla larga con top-K similares
      3. run_info_<modelo>.txt           → log legible de la ejecución
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    model_tag = sanitize_model_name(model_name)

    # 1. Matriz de similitud cuadrada (filas y columnas = paper_id)
    sim_df = pd.DataFrame(
        sim_matrix,
        index=df["paper_id"].tolist(),
        columns=df["paper_id"].tolist(),
    )
    sim_path = output_dir / f"similarity_matrix_{model_tag}.csv"
    sim_df.to_csv(sim_path)
    print(f"[OK] Matriz de similitud guardada en: {sim_path}")

    # 2. Top-K papers similares en formato largo
    top_k_path = output_dir / f"top3_similar_{model_tag}.csv"
    top_k_df.to_csv(top_k_path, index=False)
    print(f"[OK] Top-{top_k} similares guardados en: {top_k_path}")

    # 3. Fichero de log de la ejecución
    run_info_path = output_dir / f"run_info_{model_tag}.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(run_info_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("        ABSTRACT SIMILARITY — RUN INFO\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Fecha y hora de ejecución : {timestamp}\n")
        f.write(f"Modelo usado              : {model_name}\n")
        f.write(f"Archivo de entrada        : {input_path.resolve()}\n")
        f.write(f"Directorio de salida      : {output_dir.resolve()}\n")
        f.write(f"Papers procesados (válidos): {len(df)}\n")
        f.write(f"Top-K                     : {top_k}\n\n")
        f.write("Notas sobre la limpieza de datos:\n")
        f.write(f"  - Filas eliminadas por abstract vacío/nulo : {n_dropped_abstract}\n")
        f.write(f"  - Filas eliminadas por paper_id duplicado  : {n_dropped_dedup}\n\n")
        f.write("Estrategia de prefijo para E5:\n")
        if "e5" in model_name.lower():
            f.write(
                "  Se usó el prefijo 'passage: ' para todos los abstracts,\n"
                "  ya que todos actúan como textos a indexar/comparar entre sí.\n"
            )
        else:
            f.write("  No se aplicó ningún prefijo (modelo no-E5).\n")
        f.write("\nNormalización:\n")
        f.write("  Los embeddings se normalizaron a norma L2 unitaria antes\n")
        f.write("  del cálculo de similitud coseno.\n\n")
        f.write("Archivos generados:\n")
        f.write(f"  - {sim_path.name}\n")
        f.write(f"  - {top_k_path.name}\n")
        f.write(f"  - {run_info_path.name}\n")
    print(f"[OK] Log de ejecución guardado en: {run_info_path}")

    # 4. Generar similarities.csv para la integración en RDF (build_rdf.py)
    # Se filtran parejas con similitud coseno >= 0.75 (umbral ontológico definido)
    sim_threshold = 0.6
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    similarities_path = processed_dir / "similarities.csv"

    sim_rows = []
    n = len(df)
    for i in range(n):
        for j in range(i + 1, n):
            score = float(sim_matrix[i, j])
            if score >= sim_threshold:
                sim_rows.append({
                    "paper_id_source": df.loc[i, "paper_id"],
                    "paper_id_target": df.loc[j, "paper_id"],
                    "similarity_score": round(score, 6),
                    "threshold": sim_threshold,
                    "model_used": model_name
                })

    sim_df_processed = pd.DataFrame(sim_rows)
    if sim_df_processed.empty:
        sim_df_processed = pd.DataFrame(columns=["paper_id_source", "paper_id_target", "similarity_score", "threshold", "model_used"])

    # Se guarda con sep=";" para alinearse estrictamente con build_rdf.py
    sim_df_processed.to_csv(similarities_path, index=False, sep=";")
    print(f"[OK] Fichero de integración en RDF guardado en: {similarities_path} (Parejas >= {sim_threshold}: {len(sim_rows)})")



# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    print("\n" + "=" * 60)
    print("   ABSTRACT SIMILARITY — Knowledge Graph de Lesiones Deportivas")
    print("=" * 60 + "\n")

    # --- 1. Carga y limpieza de datos ---
    if not INPUT_CSV.exists():
        print(f"[ERROR] No se encontró el archivo de entrada: {INPUT_CSV.resolve()}")
        print(
            "Asegúrate de que INPUT_CSV apunta al CSV correcto "
            "(con columnas: paper_id, title, abstract)."
        )
        sys.exit(1)

    df_raw_len_before = len(pd.read_csv(INPUT_CSV, sep=CSV_SEPARATOR, dtype=str))
    df = load_data(INPUT_CSV)

    # Calcular cuántos se eliminaron en cada paso (para el log)
    n_dropped_abstract = df_raw_len_before - len(df)  # simplificado
    n_dropped_dedup = 0  # ya registrado internamente en load_data

    # --- 2. Preparación de textos ---
    texts = prepare_texts(df, MODEL_NAME)

    # --- 3. Generación de embeddings ---
    embeddings = generate_embeddings(texts, MODEL_NAME)

    # --- 4. Cálculo de la matriz de similitud ---
    sim_matrix = compute_similarity_matrix(embeddings)

    # --- 5. Top-K papers similares ---
    top_k_df = get_top_k_similar(df, sim_matrix, TOP_K)

    # --- 6. Guardado de resultados ---
    save_outputs(
        df=df,
        sim_matrix=sim_matrix,
        top_k_df=top_k_df,
        input_path=INPUT_CSV,
        output_dir=OUTPUT_DIR,
        model_name=MODEL_NAME,
        top_k=TOP_K,
        n_dropped_abstract=n_dropped_abstract,
        n_dropped_dedup=n_dropped_dedup,
    )

    print("\n[DONE] Proceso completado con éxito.\n")


if __name__ == "__main__":
    main()
