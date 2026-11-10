BEGIN ISOLATION LEVEL REPEATABLE READ;
LOCK TABLE
    "public"."table1",
    "public"."table2",
    "public"."table3",
    "public"."table4",
    "public"."table5",
    "public"."table6"
IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE "pgdm_cross_table_hash_manifest" ON COMMIT DROP AS
SELECT
    "raw_schema"::text AS raw_schema,
    "raw_hash"::text AS raw_hash,
    COUNT(*)::bigint AS row_count
FROM "public"."raw_data"
WHERE "raw_schema" IN ('group001')
GROUP BY "raw_schema", "raw_hash";

DO $pgdm_expansion_scope$
DECLARE
    missing_schemas text;
BEGIN
    SELECT string_agg(expected.raw_schema, ', ' ORDER BY expected.raw_schema)
    INTO missing_schemas
    FROM unnest(ARRAY['group001']::text[]) AS expected(raw_schema)
    WHERE NOT EXISTS (
        SELECT 1
        FROM "pgdm_cross_table_hash_manifest" AS actual
        WHERE actual.raw_schema = expected.raw_schema
    );

    IF missing_schemas IS NOT NULL THEN
        RAISE EXCEPTION
            'raw_schema has no source rows: %.',
            missing_schemas;
    END IF;
END
$pgdm_expansion_scope$;

SELECT json_build_object(
    'raw_schemas', to_json(ARRAY['group001']::text[]),
    'expected_row_count', COALESCE((
        SELECT SUM(row_count)
        FROM "pgdm_cross_table_hash_manifest"
    ), 0),
    'expected_distinct_raw_hash_count', (
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT raw_hash
            FROM "pgdm_cross_table_hash_manifest"
        ) AS distinct_hashes
    ),
    'raw_hash_manifest', COALESCE((
        SELECT json_agg(
            json_build_object(
                'raw_schema', raw_schema,
                'raw_hash', raw_hash,
                'row_count', row_count
            )
            ORDER BY raw_schema, raw_hash NULLS FIRST
        )
        FROM "pgdm_cross_table_hash_manifest"
    ), '[]'::json),
    'source_columns', COALESCE((
        SELECT json_agg(
            json_build_object(
                'name', attribute.attname,
                'type', pg_catalog.format_type(attribute.atttypid, attribute.atttypmod)
            )
            ORDER BY attribute.attnum
        )
        FROM pg_attribute AS attribute
        JOIN pg_class AS relation
          ON relation.oid = attribute.attrelid
        JOIN pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = 'public'
          AND relation.relname = 'raw_data'
          AND relation.relkind IN ('r', 'p')
          AND attribute.attnum > 0
          AND NOT attribute.attisdropped
    ), '[]'::json)
)::text;

DO $pgdm_managed_sql$
DECLARE
    pgdm_affected_rows bigint;
BEGIN
    INSERT INTO public.table3 (
    text_column_1,
    text_column_2,
    numeric_column_1,
    text_column_3,
    text_column_4
)
SELECT DISTINCT
    BTRIM(source_row.raw -> 'values' ->> 'text_column_1'),
    'SYNTHETIC/REFERENCE',
    NULL::numeric,
    LEFT(UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_2')), 1),
    RIGHT(UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_2')), 1)
FROM (
    SELECT *
    FROM "public"."raw_data"
    WHERE "raw_schema" IN ('group001')
) AS source_row
WHERE BTRIM(source_row.raw -> 'values' ->> 'text_column_1') <> ''
  AND UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_2')) ~ '^[A-Z]{2}$'
    ;
    GET DIAGNOSTICS pgdm_affected_rows = ROW_COUNT;

    UPDATE "public"."pgdm_table_row_counts"
    SET row_count = row_count + pgdm_affected_rows,
        updated_at = clock_timestamp()
    WHERE schema_name = 'public'
      AND table_name = 'table3';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Contador ausente para %.% durante insercao.',
            'public',
            'table3';
    END IF;

END
$pgdm_managed_sql$;

DO $pgdm_managed_sql$
DECLARE
    pgdm_affected_rows bigint;
BEGIN
    INSERT INTO public.table4 (
    id_column_1,
    text_column_1,
    text_column_2
)
SELECT DISTINCT
    (
        (ASCII(LEFT(UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_3')), 1))
            - ASCII('A')) * 26
        + ASCII(RIGHT(UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_3')), 1))
        - ASCII('A')
        + 1
    )::smallint,
    'SYNTHETIC/GENERIC',
    UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_3'))
FROM (
    SELECT *
    FROM "public"."raw_data"
    WHERE "raw_schema" IN ('group001')
) AS source_row
WHERE UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_3')) ~ '^[A-Z]{2}$'
    ;
    GET DIAGNOSTICS pgdm_affected_rows = ROW_COUNT;

    UPDATE "public"."pgdm_table_row_counts"
    SET row_count = row_count + pgdm_affected_rows,
        updated_at = clock_timestamp()
    WHERE schema_name = 'public'
      AND table_name = 'table4';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Contador ausente para %.% durante insercao.',
            'public',
            'table4';
    END IF;

END
$pgdm_managed_sql$;

DO $pgdm_managed_sql$
DECLARE
    pgdm_affected_rows bigint;
BEGIN
    INSERT INTO public.table1 (
    id_column_2,
    text_column_1,
    datetime_column_1,
    text_column_2,
    integer_column_1,
    integer_column_2,
    integer_column_3,
    text_column_3,
    id_column_3,
    id_column_4,
    id_column_5,
    integer_column_4,
    integer_column_5,
    id_column_6,
    integer_column_6,
    integer_column_7
)
SELECT
    NULLIF(BTRIM(source_row.raw -> 'values' ->> 'id_column_1'), '')::integer,
    NULL::character varying,
    NULLIF(BTRIM(source_row.raw -> 'values' ->> 'datetime_column_1'), '')::timestamptz
        AT TIME ZONE 'America/Sao_Paulo',
    NULL::character varying,
    GREATEST(
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_2'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_3'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_4'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_5'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_6'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_7'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_8'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_9'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_10'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_11'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_12'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_13'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_14'), '')::smallint,
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_15'), '')::smallint
    ),
    NULL::smallint,
    CASE
        WHEN NULLIF(BTRIM(source_row.raw -> 'values' ->> 'numeric_column_2'), '')::numeric > 0
        THEN ROUND(
            NULLIF(BTRIM(source_row.raw -> 'values' ->> 'numeric_column_2'), '')::numeric * 1000
        )::integer
        ELSE NULL::integer
    END,
    NULL::character varying,
    source_row.raw_id,
    dimension_row.id_column_1,
    NULL::bigint,
    NULL::integer,
    NULL::integer,
    NULL::integer,
    NULL::integer,
    CASE
        WHEN NULLIF(BTRIM(source_row.raw -> 'values' ->> 'numeric_column_1'), '')::numeric > 0
        THEN ROUND(
            NULLIF(BTRIM(source_row.raw -> 'values' ->> 'numeric_column_1'), '')::numeric * 1000
        )::integer
        ELSE NULL::integer
    END
FROM (
    SELECT *
    FROM "public"."raw_data"
    WHERE "raw_schema" IN ('group001')
) AS source_row
JOIN public.table3 AS dimension_row
  ON dimension_row.text_column_1 = BTRIM(source_row.raw -> 'values' ->> 'text_column_1')
 AND dimension_row.text_column_2 = 'SYNTHETIC/REFERENCE'
 AND dimension_row.numeric_column_1 IS NULL
 AND dimension_row.text_column_3 = LEFT(
        UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_2')),
        1
    )
 AND dimension_row.text_column_4 = RIGHT(
        UPPER(BTRIM(source_row.raw -> 'values' ->> 'text_column_2')),
        1
    )
    ;
    GET DIAGNOSTICS pgdm_affected_rows = ROW_COUNT;

    UPDATE "public"."pgdm_table_row_counts"
    SET row_count = row_count + pgdm_affected_rows,
        updated_at = clock_timestamp()
    WHERE schema_name = 'public'
      AND table_name = 'table1';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Contador ausente para %.% durante insercao.',
            'public',
            'table1';
    END IF;

END
$pgdm_managed_sql$;

DO $pgdm_managed_sql$
DECLARE
    pgdm_affected_rows bigint;
BEGIN
    INSERT INTO public.table5 (
    numeric_column_1,
    numeric_column_2,
    integer_column_1,
    integer_column_2,
    id_column_2,
    id_column_3
)
SELECT
    ROUND(
        NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_1'), '')::numeric,
        1
    ),
    NULL::numeric,
    NULL::integer,
    NULL::integer,
    main_row.id_column_1,
    NULL::bigint
FROM (
    SELECT *
    FROM "public"."raw_data"
    WHERE "raw_schema" IN ('group001')
) AS source_row
JOIN public.table1 AS main_row
  ON main_row.id_column_3 = source_row.raw_id
WHERE NULLIF(BTRIM(source_row.raw -> 'values' ->> 'integer_column_1'), '')::numeric > 0
    ;
    GET DIAGNOSTICS pgdm_affected_rows = ROW_COUNT;

    UPDATE "public"."pgdm_table_row_counts"
    SET row_count = row_count + pgdm_affected_rows,
        updated_at = clock_timestamp()
    WHERE schema_name = 'public'
      AND table_name = 'table5';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Contador ausente para %.% durante insercao.',
            'public',
            'table5';
    END IF;

END
$pgdm_managed_sql$;

DO $pgdm_managed_sql$
DECLARE
    pgdm_affected_rows bigint;
BEGIN
    INSERT INTO public.table6 (
    id_column_2,
    id_column_3
)
SELECT
    main_row.id_column_1,
    reference_row.id_column_1
FROM (
    SELECT *
    FROM "public"."raw_data"
    WHERE "raw_schema" IN ('group001')
) AS source_row
JOIN public.table1 AS main_row
  ON main_row.id_column_3 = source_row.raw_id
JOIN public.table4 AS reference_row
  ON reference_row.text_column_1 = 'SYNTHETIC/GENERIC'
 AND reference_row.text_column_2 = UPPER(
        BTRIM(source_row.raw -> 'values' ->> 'text_column_3')
    )
    ;
    GET DIAGNOSTICS pgdm_affected_rows = ROW_COUNT;

    UPDATE "public"."pgdm_table_row_counts"
    SET row_count = row_count + pgdm_affected_rows,
        updated_at = clock_timestamp()
    WHERE schema_name = 'public'
      AND table_name = 'table6';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Contador ausente para %.% durante insercao.',
            'public',
            'table6';
    END IF;

END
$pgdm_managed_sql$;

DO $pgdm_managed_sql$
DECLARE
    pgdm_affected_rows bigint;
BEGIN
    INSERT INTO public.table2 (
    id_column_2,
    integer_column_1,
    integer_column_2,
    text_column_1,
    integer_column_3,
    integer_column_4,
    integer_column_5,
    integer_column_6
)
SELECT
    main_row.id_column_1,
    position_data.position_number,
    ROUND(
        NULLIF(BTRIM(position_data.weight_text), '')::numeric * 1000
    )::integer,
    UPPER(BTRIM(position_data.type_text)),
    NULL::integer,
    NULL::integer,
    NULL::integer,
    CASE
        WHEN NULLIF(BTRIM(position_data.gap_text), '')::numeric > 0
        THEN ROUND(
            NULLIF(BTRIM(position_data.gap_text), '')::numeric * 1000
        )::integer
        ELSE NULL::integer
    END
FROM (
    SELECT *
    FROM "public"."raw_data"
    WHERE "raw_schema" IN ('group001')
) AS source_row
CROSS JOIN LATERAL (
    VALUES
        (1::smallint, source_row.raw -> 'values' ->> 'integer_column_2', source_row.raw -> 'values' ->> 'text_column_4', source_row.raw -> 'values' ->> 'numeric_column_3', source_row.raw -> 'values' ->> 'numeric_column_4'),
        (2::smallint, source_row.raw -> 'values' ->> 'integer_column_3', source_row.raw -> 'values' ->> 'text_column_5', source_row.raw -> 'values' ->> 'numeric_column_5', source_row.raw -> 'values' ->> 'numeric_column_6'),
        (3::smallint, source_row.raw -> 'values' ->> 'integer_column_4', source_row.raw -> 'values' ->> 'text_column_6', source_row.raw -> 'values' ->> 'numeric_column_7', source_row.raw -> 'values' ->> 'numeric_column_8'),
        (4::smallint, source_row.raw -> 'values' ->> 'integer_column_5', source_row.raw -> 'values' ->> 'text_column_7', source_row.raw -> 'values' ->> 'numeric_column_9', source_row.raw -> 'values' ->> 'numeric_column_10'),
        (5::smallint, source_row.raw -> 'values' ->> 'integer_column_6', source_row.raw -> 'values' ->> 'text_column_8', source_row.raw -> 'values' ->> 'numeric_column_11', source_row.raw -> 'values' ->> 'numeric_column_12'),
        (6::smallint, source_row.raw -> 'values' ->> 'integer_column_7', source_row.raw -> 'values' ->> 'text_column_9', source_row.raw -> 'values' ->> 'numeric_column_13', source_row.raw -> 'values' ->> 'numeric_column_14'),
        (7::smallint, source_row.raw -> 'values' ->> 'integer_column_8', source_row.raw -> 'values' ->> 'text_column_10', source_row.raw -> 'values' ->> 'numeric_column_15', source_row.raw -> 'values' ->> 'numeric_column_16'),
        (8::smallint, source_row.raw -> 'values' ->> 'integer_column_9', source_row.raw -> 'values' ->> 'text_column_11', source_row.raw -> 'values' ->> 'numeric_column_17', source_row.raw -> 'values' ->> 'numeric_column_18'),
        (9::smallint, source_row.raw -> 'values' ->> 'integer_column_10', source_row.raw -> 'values' ->> 'text_column_12', source_row.raw -> 'values' ->> 'numeric_column_19', source_row.raw -> 'values' ->> 'numeric_column_20'),
        (10::smallint, source_row.raw -> 'values' ->> 'integer_column_11', source_row.raw -> 'values' ->> 'text_column_13', source_row.raw -> 'values' ->> 'numeric_column_21', source_row.raw -> 'values' ->> 'numeric_column_22'),
        (11::smallint, source_row.raw -> 'values' ->> 'integer_column_12', source_row.raw -> 'values' ->> 'text_column_14', source_row.raw -> 'values' ->> 'numeric_column_23', source_row.raw -> 'values' ->> 'numeric_column_24'),
        (12::smallint, source_row.raw -> 'values' ->> 'integer_column_13', source_row.raw -> 'values' ->> 'text_column_15', source_row.raw -> 'values' ->> 'numeric_column_25', source_row.raw -> 'values' ->> 'numeric_column_26'),
        (13::smallint, source_row.raw -> 'values' ->> 'integer_column_14', source_row.raw -> 'values' ->> 'text_column_16', source_row.raw -> 'values' ->> 'numeric_column_27', source_row.raw -> 'values' ->> 'numeric_column_28'),
        (14::smallint, source_row.raw -> 'values' ->> 'integer_column_15', source_row.raw -> 'values' ->> 'text_column_17', source_row.raw -> 'values' ->> 'numeric_column_29', source_row.raw -> 'values' ->> 'numeric_column_30')
) AS position_data(position_number, declared_number_text, type_text, weight_text, gap_text)
JOIN public.table1 AS main_row
  ON main_row.id_column_3 = source_row.raw_id
WHERE NULLIF(BTRIM(position_data.declared_number_text), '')::smallint
        = position_data.position_number
  AND NULLIF(BTRIM(position_data.weight_text), '')::numeric >= 0
  AND UPPER(BTRIM(position_data.type_text)) IN ('X', 'Y', 'Z')
    ;
    GET DIAGNOSTICS pgdm_affected_rows = ROW_COUNT;

    UPDATE "public"."pgdm_table_row_counts"
    SET row_count = row_count + pgdm_affected_rows,
        updated_at = clock_timestamp()
    WHERE schema_name = 'public'
      AND table_name = 'table2';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Contador ausente para %.% durante insercao.',
            'public',
            'table2';
    END IF;

END
$pgdm_managed_sql$;
COMMIT;
