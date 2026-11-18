-- Executado automaticamente pela imagem oficial do Postgres na PRIMEIRA vez que o
-- container sobe com um volume vazio (pasta docker-entrypoint-initdb.d).
-- Cria o banco usado pelos testes automatizados (backend/tests), separado do banco
-- de desenvolvimento (esse é criado pela própria imagem via POSTGRES_DB).
CREATE DATABASE kijapa_db_test;
