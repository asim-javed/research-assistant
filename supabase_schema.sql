-- SQL for Supabase schema
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL
);

CREATE TABLE reference_sets (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  name TEXT
);

CREATE TABLE documents (
  id UUID PRIMARY KEY,
  reference_set_id UUID REFERENCES reference_sets(id),
  name TEXT,
  path TEXT
);

CREATE TABLE inquiries (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  title TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE inquiry_messages (
  id UUID PRIMARY KEY,
  inquiry_id UUID REFERENCES inquiries(id),
  message TEXT,
  response TEXT,
  timestamp TIMESTAMP DEFAULT now()
);