import psycopg2

CHUNK_SIZE = 500  # quantidade de registros por lote

def migrar_dados():
    conn = psycopg2.connect(
        dbname="postagens",
        user="walter",
        password="walterpass",
        host="localhost",
        port="5433"
    )
    cursor = conn.cursor()

    offset = 0
    total = 0

    while True:
        cursor.execute(f"""
            SELECT nome_arquivo, legenda, titulo, status, status_youtube,
                   data_criacao, data_postagem, data_post_youtube
            FROM public.fabio
            ORDER BY id
            LIMIT {CHUNK_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()

        if not rows:
            break  # fim da migração

        insert_query = """
            INSERT INTO public.modoprotylty
            (nome_arquivo, legenda, titulo, status, status_youtube,
             data_criacao, data_postagem, data_post_youtube)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_query, rows)
        conn.commit()

        total += len(rows)
        print(f"{len(rows)} registros migrados (offset {offset})")

        offset += CHUNK_SIZE

    cursor.close()
    conn.close()
    print(f"Migração concluída ✅ Total migrado: {total}")

def main():
    migrar_dados()

if __name__ == "__main__":
    main()
