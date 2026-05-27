SELECT 'CREATE DATABASE all_pdfs_chat_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'all_pdfs_chat_test')\gexec
