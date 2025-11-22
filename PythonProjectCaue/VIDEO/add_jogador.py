import psycopg2

DB_CONFIG = {
    "dbname": "n8n",
    "user": "n8n",
    "password": "n8npass",
    "host": "localhost",
    "port": "5432"
}

TAG = "#jogador"


def add_tag(texto):
    if texto is None:
        return None
    texto = texto.strip()
    if TAG.lower() in texto.lower():
        return texto
    return texto + " " + TAG


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    total_atualizados = 0

    try:
        with conn.cursor() as cur:
            # seleciona todos os registros que precisam de atualização
            cur.execute("""
                SELECT id, titulo, legenda
                FROM lucastylty_sc
                WHERE (titulo IS NOT NULL AND titulo NOT ILIKE '%#jogador%')
                   OR (legenda IS NOT NULL AND legenda NOT ILIKE '%#jogador%')
                ORDER BY id
            """)

            rows = cur.fetchall()
            print(f"Registros encontrados para atualização: {len(rows)}")

            for rid, titulo, legenda in rows:
                novo_titulo = add_tag(titulo)
                nova_legenda = add_tag(legenda)

                if novo_titulo != titulo or nova_legenda != legenda:
                    cur.execute("""
                        UPDATE lucastylty_sc
                        SET titulo = %s,
                            legenda = %s
                        WHERE id = %s
                    """, (novo_titulo, nova_legenda, rid))
                    total_atualizados += 1

            conn.commit()
        print(f"Processo concluído! Total de registros atualizados: {total_atualizados}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
