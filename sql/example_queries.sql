-- Example SQL Operations for Competitive Intelligence System
-- These demonstrate the workflow from raw fetch to approved intelligence

-- 1. INSERT a new raw fetch from scraper
INSERT INTO raw_fetch_queue (
    competitor_id,
    url,
    title,
    content,
    published_date,
    confidence_score,
    metadata
) VALUES (
    (SELECT id FROM competitors WHERE name = 'Snowflake'),
    'https://www.snowflake.com/blog/announcing-snowpark-python',
    'Announcing Snowpark for Python',
    'Snowflake today announced the general availability of Snowpark for Python...',
    '2025-08-06 10:00:00-07',
    85.5,
    '{"source": "blog", "category": "product_announcement"}'::jsonb
);

-- 2. QUERY pending items for triage (dashboard view)
SELECT 
    rfq.id,
    c.name as competitor,
    rfq.title,
    rfq.published_date,
    rfq.confidence_score,
    rfq.fetched_at,
    rfq.status
FROM raw_fetch_queue rfq
JOIN competitors c ON rfq.competitor_id = c.id
WHERE rfq.status = 'pending'
ORDER BY rfq.confidence_score DESC, rfq.fetched_at DESC
LIMIT 50;

-- 3. APPROVE a raw fetch and move to competitive updates
WITH approved_fetch AS (
    UPDATE raw_fetch_queue 
    SET 
        status = 'approved',
        processed_at = CURRENT_TIMESTAMP,
        processed_by = (SELECT id FROM users WHERE email = 'pm@company.com')
    WHERE id = 'raw-fetch-uuid-here'
    RETURNING *
)
INSERT INTO competitor_updates (
    competitor_id,
    raw_fetch_id,
    title,
    summary,
    url,
    published_date,
    relevance_category,
    strategic_priority,
    confidence_score,
    approved_by,
    pm_notes
)
SELECT 
    af.competitor_id,
    af.id,
    af.title,
    LEFT(af.content, 500) || '...' as summary,
    af.url,
    af.published_date,
    'product_launch',
    'high',
    af.confidence_score,
    af.processed_by,
    'Critical Python support announcement - impacts our data science positioning'
FROM approved_fetch af;

-- 4. REJECT a raw fetch with reason
UPDATE raw_fetch_queue 
SET 
    status = 'rejected',
    processed_at = CURRENT_TIMESTAMP,
    processed_by = (SELECT id FROM users WHERE email = 'pm@company.com'),
    rejection_reason = 'Not relevant to our competitive analysis - internal hiring post'
WHERE id = 'raw-fetch-uuid-to-reject';

-- 5. DEDUPLICATE - Check if URL already exists before inserting
WITH url_hash AS (
    SELECT encode(sha256('https://example.com/blog/post'::bytea), 'hex') as hash
)
INSERT INTO url_fingerprints (url_hash, original_url, competitor_id)
SELECT 
    uh.hash,
    'https://example.com/blog/post',
    (SELECT id FROM competitors WHERE name = 'Databricks')
FROM url_hash uh
WHERE NOT EXISTS (
    SELECT 1 FROM url_fingerprints WHERE url_hash = uh.hash
);

-- 6. DASHBOARD QUERY - High priority competitive updates from last 30 days
SELECT 
    cu.id,
    c.name as competitor,
    cu.title,
    cu.summary,
    cu.relevance_category,
    cu.strategic_priority,
    cu.confidence_score,
    cu.published_date,
    cu.approved_at,
    u.name as approved_by_name,
    cu.pm_notes
FROM competitor_updates cu
JOIN competitors c ON cu.competitor_id = c.id
JOIN users u ON cu.approved_by = u.id
WHERE 
    cu.strategic_priority = 'high'
    AND cu.published_date >= CURRENT_DATE - INTERVAL '30 days'
    AND cu.is_archived = false
ORDER BY cu.published_date DESC, cu.confidence_score DESC;

-- 7. SEARCH across approved updates
SELECT 
    cu.id,
    c.name as competitor,
    cu.title,
    cu.summary,
    cu.relevance_category,
    cu.published_date,
    ts_rank(to_tsvector('english', cu.title || ' ' || COALESCE(cu.summary, '') || ' ' || COALESCE(cu.pm_notes, '')), 
            to_tsquery('english', 'machine & learning')) as rank
FROM competitor_updates cu
JOIN competitors c ON cu.competitor_id = c.id
WHERE 
    to_tsvector('english', cu.title || ' ' || COALESCE(cu.summary, '') || ' ' || COALESCE(cu.pm_notes, ''))
    @@ to_tsquery('english', 'machine & learning')
    AND cu.is_archived = false
ORDER BY rank DESC, cu.published_date DESC;

-- 8. ANALYTICS - Competitive activity summary by month
SELECT 
    c.name as competitor,
    DATE_TRUNC('month', cu.published_date) as month,
    COUNT(*) as total_updates,
    COUNT(*) FILTER (WHERE cu.strategic_priority = 'high') as high_priority_count,
    ROUND(AVG(cu.confidence_score), 2) as avg_confidence
FROM competitor_updates cu
JOIN competitors c ON cu.competitor_id = c.id
WHERE 
    cu.published_date >= CURRENT_DATE - INTERVAL '6 months'
    AND cu.is_archived = false
GROUP BY c.name, DATE_TRUNC('month', cu.published_date)
ORDER BY month DESC, total_updates DESC;

-- 9. UPDATE an existing competitive update
UPDATE competitor_updates 
SET 
    strategic_priority = 'high',
    pm_notes = 'Updated priority after team discussion - this directly competes with our Q4 roadmap',
    updated_at = CURRENT_TIMESTAMP
WHERE id = 'competitor-update-uuid-here';

-- 10. ARCHIVE old updates (cleanup job)
UPDATE competitor_updates 
SET 
    is_archived = true,
    updated_at = CURRENT_TIMESTAMP
WHERE 
    published_date < CURRENT_DATE - INTERVAL '2 years'
    AND is_archived = false;

-- USEFUL VIEWS for the application

-- View: Latest competitive intelligence dashboard
CREATE OR REPLACE VIEW dashboard_recent_intel AS
SELECT 
    cu.id,
    c.name as competitor,
    cu.title,
    cu.summary,
    cu.url,
    cu.relevance_category,
    cu.strategic_priority,
    cu.confidence_score,
    cu.published_date,
    cu.approved_at,
    u.name as approved_by_name,
    cu.pm_notes,
    CASE 
        WHEN cu.published_date >= CURRENT_DATE - INTERVAL '1 day' THEN 'today'
        WHEN cu.published_date >= CURRENT_DATE - INTERVAL '7 days' THEN 'this_week'
        WHEN cu.published_date >= CURRENT_DATE - INTERVAL '30 days' THEN 'this_month'
        ELSE 'older'
    END as recency
FROM competitor_updates cu
JOIN competitors c ON cu.competitor_id = c.id
JOIN users u ON cu.approved_by = u.id
WHERE cu.is_archived = false
ORDER BY cu.published_date DESC;

-- View: Pending triage queue with metadata
CREATE OR REPLACE VIEW triage_queue AS
SELECT 
    rfq.id,
    c.name as competitor,
    rfq.title,
    LEFT(rfq.content, 300) || '...' as content_preview,
    rfq.url,
    rfq.published_date,
    rfq.confidence_score,
    rfq.fetched_at,
    rfq.metadata,
    CASE 
        WHEN rfq.confidence_score >= 80 THEN 'high_confidence'
        WHEN rfq.confidence_score >= 60 THEN 'medium_confidence'
        ELSE 'low_confidence'
    END as confidence_level
FROM raw_fetch_queue rfq
JOIN competitors c ON rfq.competitor_id = c.id
WHERE rfq.status = 'pending'
ORDER BY rfq.confidence_score DESC, rfq.fetched_at DESC;
