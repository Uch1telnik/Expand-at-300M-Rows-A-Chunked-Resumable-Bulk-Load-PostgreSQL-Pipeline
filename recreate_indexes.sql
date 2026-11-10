-- 1) rebuild every unique index / PK / UNIQUE constraint first
CREATE UNIQUE INDEX table1_pkey ON public.table1 (id_column_1);
ALTER TABLE public.table1 ADD CONSTRAINT table1_pkey PRIMARY KEY USING INDEX table1_pkey;
CREATE UNIQUE INDEX table1_id_column_3_key ON public.table1 (id_column_3);
ALTER TABLE public.table1 ADD CONSTRAINT table1_id_column_3_key UNIQUE USING INDEX table1_id_column_3_key;

CREATE UNIQUE INDEX table2_pkey ON public.table2 (id_column_1);
ALTER TABLE public.table2 ADD CONSTRAINT table2_pkey PRIMARY KEY USING INDEX table2_pkey;
CREATE UNIQUE INDEX table2_id_column_2_integer_column_1_key ON public.table2 (id_column_2, integer_column_1);
ALTER TABLE public.table2 ADD CONSTRAINT table2_id_column_2_integer_column_1_key UNIQUE USING INDEX table2_id_column_2_integer_column_1_key;

CREATE UNIQUE INDEX table3_pkey ON public.table3 (id_column_1);
ALTER TABLE public.table3 ADD CONSTRAINT table3_pkey PRIMARY KEY USING INDEX table3_pkey;

CREATE UNIQUE INDEX table4_pkey ON public.table4 (id_column_1);
ALTER TABLE public.table4 ADD CONSTRAINT table4_pkey PRIMARY KEY USING INDEX table4_pkey;

CREATE UNIQUE INDEX table5_pkey ON public.table5 (id_column_1);
ALTER TABLE public.table5 ADD CONSTRAINT table5_pkey PRIMARY KEY USING INDEX table5_pkey;
CREATE UNIQUE INDEX table5_id_column_2_when_id_column_3_null_key ON public.table5 (id_column_2) WHERE id_column_3 IS NULL;
CREATE UNIQUE INDEX table5_id_column_3_not_null_key ON public.table5 (id_column_3) WHERE id_column_3 IS NOT NULL;

CREATE UNIQUE INDEX table6_pkey ON public.table6 (id_column_1);
ALTER TABLE public.table6 ADD CONSTRAINT table6_pkey PRIMARY KEY USING INDEX table6_pkey;
CREATE UNIQUE INDEX table6_id_column_2_id_column_3_key ON public.table6 (id_column_2, id_column_3);
ALTER TABLE public.table6 ADD CONSTRAINT table6_id_column_2_id_column_3_key UNIQUE USING INDEX table6_id_column_2_id_column_3_key;

-- 2) re-validate foreign keys last, once all unique keys exist
ALTER TABLE public.table1 ADD CONSTRAINT table1_id_column_3_fkey FOREIGN KEY (id_column_3) REFERENCES public.raw_data(raw_id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table1 ADD CONSTRAINT table1_id_column_4_fkey FOREIGN KEY (id_column_4) REFERENCES public.table3(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table2 ADD CONSTRAINT table2_id_column_2_fkey FOREIGN KEY (id_column_2) REFERENCES public.table1(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table5 ADD CONSTRAINT table5_id_column_2_fkey FOREIGN KEY (id_column_2) REFERENCES public.table1(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table6 ADD CONSTRAINT table6_id_column_2_fkey FOREIGN KEY (id_column_2) REFERENCES public.table1(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.table6 ADD CONSTRAINT table6_id_column_3_fkey FOREIGN KEY (id_column_3) REFERENCES public.table4(id_column_1) ON UPDATE CASCADE ON DELETE CASCADE;
