use app;

-- テストユーザーの追加
INSERT INTO `user` (`name`, `hashed_password`, `authority`, `created_at`, `updated_at`)
VALUES
('testuser', '$2b$12$5ph4vtVGuo8sO4Z7TrJcB.N1m0qmfBx9yIkRMwFr48NOj4dHh/TBi', 2, NOW(), NOW());
