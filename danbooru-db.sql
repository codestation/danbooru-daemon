CREATE TABLE IF NOT EXISTS "main"."post" (
    "id" INTEGER PRIMARY KEY NOT NULL,
    "width" INTEGER NOT NULL,
    "height" INTEGER NOT NULL,
    "file_size" INTEGER NOT NULL,    
    "file_url" TEXT NOT NULL,
    "author" TEXT,
    "creator_id" INTEGER,
    "rating" TEXT NOT NULL,
    "source" TEXT,
    "score"  INTEGER NOT NULL,
    "parent_id" INTEGER,
    "status" TEXT NOT NULL,
    "change" INTEGER,
    "md5" TEXT NOT NULL,
    "created_at" TEXT NOT NULL,
    "sample_url" TEXT,
    "sample_width" INTEGER,
    "sample_height" INTEGER,
    "preview_url" TEXT,
    "preview_width" INTEGER NOT NULL,
    "preview_height" INTEGER NOT NULL,
    "has_notes" INTEGER NOT NULL,
    "has_comments" INTEGER NOT NULL,
    "has_children" INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS "post_md5_idx" ON "post" ("md5");
CREATE TABLE IF NOT EXISTS "main"."post_tag" (
    "post_id" INTEGER NOT NULL,
    "tag_name"  TEXT  NOT NULL,
    PRIMARY KEY ("post_id", "tag_name"),
    FOREIGN KEY ("tag_name") REFERENCES "tag"("name")
);
CREATE TABLE IF NOT EXISTS "main"."tag" (
    "id" INTEGER PRIMARY KEY NOT NULL,
    "name" TEXT UNIQUE NOT NULL,
    "type" INTEGER,
    "ambiguous" INTEGER,
    "count" INTEGER
);
CREATE INDEX IF NOT EXISTS "tag_name_idx" ON "tag" ("name");
