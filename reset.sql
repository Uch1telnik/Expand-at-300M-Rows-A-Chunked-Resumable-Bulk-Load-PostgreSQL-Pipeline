TRUNCATE table2, table5, table6, table1, table3, table4 RESTART IDENTITY CASCADE;
UPDATE public.pgdm_table_row_counts SET row_count = 0;
SELECT (SELECT count(*) FROM table1), (SELECT count(*) FROM table2), (SELECT count(*) FROM table3), (SELECT count(*) FROM table4), (SELECT count(*) FROM table5), (SELECT count(*) FROM table6);
