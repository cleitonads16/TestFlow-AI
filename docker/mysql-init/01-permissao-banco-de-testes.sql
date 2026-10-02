-- Executado só na primeira subida do MySQL (volume vazio).
-- O pytest-django cria e apaga o banco test_casos_teste a cada execução dos
-- testes; a imagem do MySQL dá ao usuário da aplicação acesso apenas ao banco
-- casos_teste, então a permissão no banco de testes é concedida aqui.
GRANT ALL PRIVILEGES ON `test_casos_teste`.* TO 'casos_teste'@'%';
