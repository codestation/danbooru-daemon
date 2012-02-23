CREATE TABLE IF NOT EXISTS "main"."board" (
    "id" INTEGER PRIMARY KEY NOT NULL,
    "name" TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS "main"."post" (
    "id" INTEGER NOT NULL,    
    "board_id" INTEGER NOT NULL,
    "width" INTEGER,
    "height" INTEGER,
    "file_size" INTEGER,
    "file_url" TEXT NOT NULL,
    "author" TEXT,
    "creator_id" INTEGER,
    "rating" TEXT,
    "source" TEXT,
    "score"  INTEGER,
    "parent_id" INTEGER,
    "status" TEXT,
    "change" INTEGER,
    "md5" TEXT NOT NULL,
    "created_at" TEXT,
    "sample_url" TEXT,
    "sample_width" INTEGER,
    "sample_height" INTEGER,
    "preview_url" TEXT,
    "preview_width" INTEGER,
    "preview_height" INTEGER,
    "has_notes" INTEGER,
    "has_comments" INTEGER,
    "has_children" INTEGER,
    PRIMARY KEY ("id", "board_id"),
    FOREIGN KEY ("board_id") REFERENCES "board"("id")
);
CREATE INDEX IF NOT EXISTS "post_md5_idx" ON "post" ("md5");
CREATE TABLE IF NOT EXISTS "main"."post_tag" (
    "post_id" INTEGER NOT NULL,    
    "board_id" INTEGER NOT NULL,
    "tag_name" TEXT NOT NULL,    
    PRIMARY KEY ("post_id", "board_id", "tag_name"),
    FOREIGN KEY ("post_id") REFERENCES "post"("id"),
    FOREIGN KEY ("board_id") REFERENCES "board"("id")
);
CREATE TABLE IF NOT EXISTS "main"."tag" (
    "id" INTEGER NOT NULL,    
    "board_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "type" INTEGER,
    "ambiguous" INTEGER,
    "count" INTEGER,
    PRIMARY KEY ("id", "board_id"),
    FOREIGN KEY ("board_id") REFERENCES "board"("id")
);
CREATE INDEX IF NOT EXISTS "tag_name_idx" ON "tag" ("name");
