"""Initial schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260202_01_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_failed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("locked_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_successful_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "username ~ '^[a-z0-9_]{3,32}$'",
            name="ck_username_format",
        ),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(), primary_key=True),
        sa.Column(
            "granted_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "granted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )

    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text(
                "ARRAY['library:read', 'library:create', 'library:edit', 'bulletin:read', 'bulletin:write']"
            ),
        ),
        sa.Column("rate_limit_reads", sa.Integer(), server_default=sa.text("1000")),
        sa.Column("rate_limit_writes", sa.Integer(), server_default=sa.text("100")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "articles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column("current_version", sa.Integer(), server_default=sa.text("1")),
        sa.Column(
            "byte_size",
            sa.Integer(),
            sa.Computed("length(content_md)", persisted=True),
        ),
        sa.Column(
            "token_count_est",
            sa.Integer(),
            sa.Computed("length(content_md) / 4", persisted=True),
        ),
        sa.Column("tsv", postgresql.TSVECTOR()),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9-]{3,128}$'",
            name="ck_article_slug_format",
        ),
        sa.CheckConstraint("length(title) <= 500", name="ck_article_title_length"),
        sa.CheckConstraint(
            "length(content_md) <= 1048576",
            name="ck_article_content_length",
        ),
        sa.UniqueConstraint("slug", name="uq_articles_slug"),
    )

    op.create_index("idx_articles_author", "articles", ["author_id"])
    op.create_index("idx_articles_slug", "articles", ["slug"])
    op.execute("CREATE INDEX idx_articles_updated ON articles (updated_at DESC)")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION articles_tsvector_update() RETURNS trigger AS $$
        BEGIN
          NEW.tsv := to_tsvector('english', coalesce(NEW.title, '') || ' ' || coalesce(NEW.content_md, ''));
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS articles_tsvector_trigger ON articles")
    op.execute(
        """
        CREATE TRIGGER articles_tsvector_trigger
        BEFORE INSERT OR UPDATE OF title, content_md ON articles
        FOR EACH ROW EXECUTE FUNCTION articles_tsvector_update();
        """
    )
    op.create_index("idx_articles_tsv", "articles", ["tsv"], postgresql_using="gin")
    op.execute(
        """
        UPDATE articles
        SET tsv = to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content_md, ''))
        WHERE tsv IS NULL;
        """
    )

    op.create_table(
        "article_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column(
            "editor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("edit_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("article_id", "version", name="uq_article_revision_version"),
    )

    op.create_table(
        "bulletin_posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "byte_size",
            sa.Integer(),
            sa.Computed("length(content_md)", persisted=True),
        ),
        sa.Column(
            "token_count_est",
            sa.Integer(),
            sa.Computed("length(content_md) / 4", persisted=True),
        ),
        sa.CheckConstraint(
            "length(title) <= 500",
            name="ck_bulletin_post_title_length",
        ),
        sa.CheckConstraint(
            "length(content_md) <= 262144",
            name="ck_bulletin_post_content_length",
        ),
    )

    op.create_index("idx_bulletin_posts_author", "bulletin_posts", ["author_id"])
    op.execute(
        "CREATE INDEX idx_bulletin_posts_created ON bulletin_posts (created_at DESC)"
    )

    op.create_table(
        "bulletin_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bulletin_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "length(content_md) <= 65536",
            name="ck_bulletin_comment_content_length",
        ),
    )

    op.create_index(
        "idx_bulletin_comments_post",
        "bulletin_comments",
        ["post_id", "created_at"],
    )

    op.create_table(
        "bulletin_follows",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bulletin_posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("notification_type", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.execute(
        "CREATE INDEX idx_notifications_user ON notifications (user_id, created_at DESC)"
    )
    op.execute(
        """
        CREATE INDEX idx_notifications_unread
        ON notifications (user_id, created_at DESC)
        WHERE read_at IS NULL
        """
    )

    op.create_table(
        "activity_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.Enum("read", "create", "update", "delete", name="activity_action"),
            nullable=False,
        ),
        sa.Column(
            "resource",
            sa.Enum(
                "article",
                "bulletin_post",
                "bulletin_comment",
                "profile",
                "user",
                "api_key",
                name="resource_type",
            ),
            nullable=False,
        ),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "extra_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_index(
        "idx_activity_resource",
        "activity_log",
        ["resource", "resource_id", "timestamp"],
    )
    op.create_index(
        "idx_activity_user",
        "activity_log",
        ["user_id", "timestamp"],
    )
    op.create_index("idx_activity_timestamp", "activity_log", ["timestamp"])

    op.create_table(
        "rate_limit_buckets",
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("bucket_type", sa.String(), primary_key=True),
        sa.Column("window_start", sa.TIMESTAMP(timezone=True), primary_key=True),
        sa.Column("request_count", sa.Integer(), server_default=sa.text("0")),
        sa.CheckConstraint("bucket_type IN ('read', 'write')", name="ck_bucket_type"),
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "processing",
                "completed",
                "failed",
                name="idempotency_status",
            ),
            nullable=False,
            server_default=sa.text("'processing'"),
        ),
        sa.Column("response_body", postgresql.JSONB(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_index(
        "idx_idempotency_created",
        "idempotency_keys",
        ["created_at"],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_idempotency_created")
    op.drop_table("idempotency_keys")

    op.drop_table("rate_limit_buckets")

    op.drop_index("idx_activity_timestamp", table_name="activity_log")
    op.drop_index("idx_activity_user", table_name="activity_log")
    op.drop_index("idx_activity_resource", table_name="activity_log")
    op.drop_table("activity_log")

    op.execute("DROP INDEX IF EXISTS idx_notifications_unread")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user")
    op.drop_table("notifications")

    op.drop_table("bulletin_follows")

    op.drop_index("idx_bulletin_comments_post", table_name="bulletin_comments")
    op.drop_table("bulletin_comments")

    op.execute("DROP INDEX IF EXISTS idx_bulletin_posts_created")
    op.drop_index("idx_bulletin_posts_author", table_name="bulletin_posts")
    op.drop_table("bulletin_posts")

    op.drop_table("article_revisions")

    op.drop_index("idx_articles_tsv", table_name="articles")
    op.execute("DROP INDEX IF EXISTS idx_articles_updated")
    op.drop_index("idx_articles_slug", table_name="articles")
    op.drop_index("idx_articles_author", table_name="articles")
    op.execute("DROP TRIGGER IF EXISTS articles_tsvector_trigger ON articles")
    op.execute("DROP FUNCTION IF EXISTS articles_tsvector_update")
    op.drop_table("articles")

    op.drop_table("profiles")
    op.drop_table("api_keys")
    op.drop_table("user_roles")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS idempotency_status")
    op.execute("DROP TYPE IF EXISTS resource_type")
    op.execute("DROP TYPE IF EXISTS activity_action")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
