# Competitive Intelligence Dashboard - Product Management Specification

## Executive Summary

This specification outlines the evolution of the existing Flask-based competitive intelligence scraping system into a comprehensive PM-focused dashboard. The system will enhance the human-in-the-loop triage workflow, integrate roadmapping capabilities, and provide comparative analysis tools for strategic decision-making.

## Current System Analysis

**Existing Architecture:**
- PostgreSQL database with `raw_fetch_queue` (pending items) and `competitor_updates` (approved items)  
- Flask web application with basic triage actions (approve/reject/archive)
- Confidence scoring system (0-100) with AI-ready `ai_summary` field
- OpenAI integration ready (`openai==1.12.0` in requirements)

**Current Data Models:**
- **RawFetchQueue**: Scraped items awaiting triage (confidence_score, status, meta_info)
- **CompetitorUpdate**: Approved items (strategic_priority, relevance_category, pm_notes, ai_summary, tags)
- **Users**: PM/Analyst roles with approval tracking
- **Competitors**: Company reference data

## 1. Enhanced Triage Interface

### 1.1 Triage Dashboard Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ 🎯 Intelligence Triage Queue                          🔄 Auto-refresh │
├─────────────────────────────────────────────────────────────────┤
│ Filters: [All] [High Confidence] [Recent] [By Competitor ▼]    │
│ Sort: [Confidence ▼] [Date] [Company]                          │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🔴 92  Snowflake │ Enhanced Data Sharing for Enterprise... │ │
│ │ ⚡ AI Summary: Snowflake announces new cross-cloud data     │ │
│ │    sharing capabilities with enhanced security...           │ │
│ │ 📅 Jul 15, 2025 | 🔗 snowflake.com/blog/...               │ │
│ │                                                             │ │
│ │ Quick Actions:                                              │ │
│ │ [🎯 Roadmap Relevant] [💰 Pricing] [ℹ️ Need More Info]     │ │
│ │                                                             │ │
│ │ Category: [Product Launch ▼]  Priority: [High ▼]          │ │
│ │ Roadmap Theme: [Data Platform ▼] [+ New Theme]            │ │
│ │ Action Item: [________________________________]            │ │
│ │                                                             │ │
│ │ [Approve & Route] [Reject] [Archive] [View Full Article]   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🟡 78  Databricks │ New MLOps Pipeline Automation...       │ │
│ │ ⚡ AI Summary: Databricks introduces automated ML...        │ │
│ │ [Similar layout repeats for each item]                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Enhanced Data Model Additions

```sql
-- Add roadmapping fields to competitor_updates
ALTER TABLE competitor_updates ADD COLUMN roadmap_theme VARCHAR(100);
ALTER TABLE competitor_updates ADD COLUMN okr_alignment VARCHAR(200);
ALTER TABLE competitor_updates ADD COLUMN action_item TEXT;
ALTER TABLE competitor_updates ADD COLUMN impact_score INTEGER DEFAULT 50 CHECK (impact_score >= 0 AND impact_score <= 100);

-- Create roadmap themes lookup table
CREATE TABLE roadmap_themes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    color_hex VARCHAR(7), -- For UI visualization
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Create triage sessions for workflow tracking
CREATE TABLE triage_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    items_processed INTEGER DEFAULT 0,
    items_approved INTEGER DEFAULT 0,
    items_rejected INTEGER DEFAULT 0
);
```

### 1.3 React Component Pseudo-Code

```jsx
// TriageCard.jsx
const TriageCard = ({ item, onAction, themes, onUpdateTheme }) => {
  const [selectedTheme, setSelectedTheme] = useState(item.roadmap_theme);
  const [actionItem, setActionItem] = useState('');
  const [priority, setPriority] = useState('medium');
  
  const confidenceColor = item.confidence_score >= 80 ? '#f44336' : 
                         item.confidence_score >= 60 ? '#ff9800' : '#9e9e9e';
  
  return (
    <Card className="triage-card" style={{ borderLeft: `4px solid ${confidenceColor}` }}>
      <CardHeader>
        <div className="confidence-badge" style={{ backgroundColor: confidenceColor }}>
          {item.confidence_score}
        </div>
        <div className="item-meta">
          <h3>{item.competitor.name}</h3>
          <a href={item.url} target="_blank">{item.title}</a>
          <div className="meta-row">
            📅 {formatDate(item.published_date)} | 🔗 {item.url}
          </div>
        </div>
      </CardHeader>
      
      <CardBody>
        <div className="ai-summary">
          ⚡ AI Summary: {item.ai_summary || 'Generating summary...'}
        </div>
        
        <div className="quick-actions">
          <ButtonGroup>
            <Button 
              variant="success" 
              onClick={() => handleQuickAction('roadmap_relevant')}
            >
              🎯 Roadmap Relevant
            </Button>
            <Button 
              variant="warning" 
              onClick={() => handleQuickAction('pricing')}
            >
              💰 Pricing/Ignore
            </Button>
            <Button 
              variant="info" 
              onClick={() => handleQuickAction('need_info')}
            >
              ℹ️ Need More Info
            </Button>
          </ButtonGroup>
        </div>
        
        {expandedFields && (
          <div className="detailed-fields">
            <Row>
              <Col md={6}>
                <FormGroup>
                  <Label>Category</Label>
                  <Select 
                    options={categoryOptions}
                    value={selectedCategory}
                    onChange={setSelectedCategory}
                  />
                </FormGroup>
              </Col>
              <Col md={6}>
                <FormGroup>
                  <Label>Priority</Label>
                  <Select 
                    options={priorityOptions}
                    value={priority}
                    onChange={setPriority}
                  />
                </FormGroup>
              </Col>
            </Row>
            
            <FormGroup>
              <Label>Roadmap Theme</Label>
              <CreatableSelect 
                options={themes}
                value={selectedTheme}
                onChange={setSelectedTheme}
                onCreateOption={onUpdateTheme}
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Action Item</Label>
              <TextArea 
                value={actionItem}
                onChange={(e) => setActionItem(e.target.value)}
                placeholder="Brief description of what action this intelligence requires..."
              />
            </FormGroup>
          </div>
        )}
        
        <div className="action-buttons">
          <Button 
            variant="success" 
            onClick={() => onAction('approve', { 
              theme: selectedTheme, 
              actionItem, 
              priority 
            })}
          >
            Approve & Route
          </Button>
          <Button variant="secondary" onClick={() => onAction('reject')}>
            Reject
          </Button>
          <Button variant="outline" onClick={() => onAction('archive')}>
            Archive
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};
```

## 2. Roadmap Integration Module

### 2.1 Roadmap Dashboard Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ 🗺️ Roadmap Intelligence Hub                                      │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│ │ 🎯 Data Platform  │ │ 🤖 AI/ML Engine  │ │ 🔐 Security      │   │
│ │ 12 items         │ │ 8 items          │ │ 5 items          │   │
│ │ ■■■■■■■□□□ 70%   │ │ ■■■■■□□□□□ 50%   │ │ ■■■■■■■■□□ 80%   │   │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│ Recent High-Priority Intel:                                     │
│ • Snowflake: Cross-cloud data sharing (Impact: 95)             │
│ • Databricks: Automated MLOps pipeline (Impact: 87)            │
│ • BigQuery: Real-time analytics boost (Impact: 78)             │
├─────────────────────────────────────────────────────────────────┤
│ 📊 Impact vs. Urgency Matrix:                                   │
│ │High Impact  │ [■] Snowflake Data │ [■] Databricks ML │      │
│ │            │     Sharing        │     Pipeline      │      │
│ │            │────────────────────│──────────────────│      │
│ │Low Impact  │ [□] PowerBI Update │ [□] Tableau Mobile│      │
│ │            │ Low Urgency       │  High Urgency     │      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Flask Routes for Roadmap Features

```python
@app.route('/roadmap')
def roadmap_dashboard():
    """Main roadmap dashboard showing themes and intelligence alignment."""
    # Get all approved items grouped by roadmap theme
    theme_query = db.session.query(
        CompetitorUpdate.roadmap_theme,
        func.count(CompetitorUpdate.id).label('item_count'),
        func.avg(CompetitorUpdate.impact_score).label('avg_impact'),
        func.count(
            case([(CompetitorUpdate.strategic_priority == 'high', 1)])
        ).label('high_priority_count')
    ).filter(
        CompetitorUpdate.is_archived == False,
        CompetitorUpdate.roadmap_theme.isnot(None)
    ).group_by(CompetitorUpdate.roadmap_theme).all()
    
    # Get recent high-impact items
    recent_high_impact = db.session.query(CompetitorUpdate, Competitor).join(
        Competitor
    ).filter(
        CompetitorUpdate.impact_score >= 80,
        CompetitorUpdate.approved_at >= datetime.now() - timedelta(days=30),
        CompetitorUpdate.is_archived == False
    ).order_by(CompetitorUpdate.impact_score.desc()).limit(10).all()
    
    return render_template('roadmap_dashboard.html', 
                         theme_stats=theme_query,
                         high_impact_items=recent_high_impact)

@app.route('/api/roadmap/themes')
def api_roadmap_themes():
    """API to get all roadmap themes for dropdowns."""
    themes = db.session.query(RoadmapTheme).filter_by(is_active=True).all()
    return jsonify([{
        'id': theme.id,
        'name': theme.name,
        'description': theme.description,
        'color': theme.color_hex,
        'item_count': len(theme.competitor_updates)
    } for theme in themes])

@app.route('/api/triage/<uuid:item_id>/route-to-roadmap', methods=['POST'])
def route_to_roadmap(item_id):
    """Enhanced approval that routes item to specific roadmap theme."""
    data = request.get_json()
    
    # Get the raw item
    raw_item = RawFetchQueue.query.get_or_404(item_id)
    
    # Create or get roadmap theme
    theme_name = data.get('roadmap_theme')
    if theme_name and not RoadmapTheme.query.filter_by(name=theme_name).first():
        new_theme = RoadmapTheme(
            name=theme_name,
            description=f"Theme created from triage for {theme_name}",
            color_hex=generate_theme_color()  # Helper function
        )
        db.session.add(new_theme)
        db.session.flush()
    
    # Create approved update with roadmap integration
    approved_update = CompetitorUpdate(
        competitor_id=raw_item.competitor_id,
        raw_fetch_id=raw_item.id,
        title=raw_item.title,
        summary=data.get('summary', raw_item.content[:500]),
        url=raw_item.url,
        published_date=raw_item.published_date or raw_item.fetched_at,
        confidence_score=raw_item.confidence_score,
        approved_by=get_current_user().id,
        
        # Roadmap-specific fields
        roadmap_theme=theme_name,
        action_item=data.get('action_item'),
        strategic_priority=data.get('priority', 'medium'),
        impact_score=data.get('impact_score', 50),
        pm_notes=data.get('pm_notes'),
        
        # AI summary (to be populated)
        ai_summary=None  # Will be populated by background task
    )
    
    # Update raw item status
    raw_item.status = 'approved'
    raw_item.processed_at = datetime.now(timezone.utc)
    raw_item.processed_by = get_current_user().id
    
    db.session.add(approved_update)
    db.session.commit()
    
    # Trigger AI summarization background task
    generate_ai_summary.delay(approved_update.id)
    
    return jsonify({
        'success': True,
        'message': f'Item routed to {theme_name} theme',
        'update_id': str(approved_update.id)
    })
```

## 3. Comparative Analysis Views

### 3.1 Grid View - Feature Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Competitive Feature Matrix                    Export [CSV] [PDF] │
├─────────────────────────────────────────────────────────────────┤
│          │ Snowflake │Databricks│ BigQuery │ Domo    │ PowerBI   │
├──────────┼───────────┼──────────┼──────────┼─────────┼───────────┤
│Data Lake │ ✅ Q3'25  │ ✅ Q2'25 │ ⭕ Basic  │ ❌      │ ⭕ Beta   │
│Real-time │ ✅ GA     │ ✅ GA    │ ✅ NEW   │ ❌      │ ⭕ Preview │
│AI/ML Ops │ ⭕ Preview│ ✅ Leader│ ✅ GA    │ ⭕ Basic │ ⭕ Basic  │
│Cross-Clou│ ✅ NEW   │ ❌       │ ⭕ Beta  │ ❌      │ ❌        │
│Security  │ ✅ SOC2  │ ✅ SOC2 │ ✅ SOC2 │ ✅ SOC2│ ✅ SOC2  │
├──────────┼───────────┼──────────┼──────────┼─────────┼───────────┤
│ Updates  │    12     │    8     │    15    │    3    │     7     │
│ This QTR │           │          │          │         │           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Timeline Chart Component

```jsx
// CompetitiveTimeline.jsx  
const CompetitiveTimeline = ({ competitors, timeRange }) => {
  const [chartData, setChartData] = useState([]);
  
  useEffect(() => {
    // Fetch intelligence updates grouped by competitor and date
    fetch(`/api/competitive-analysis/timeline?range=${timeRange}`)
      .then(res => res.json())
      .then(data => {
        const formattedData = data.map(item => ({
          competitor: item.competitor_name,
          date: new Date(item.date),
          count: item.update_count,
          category: item.primary_category,
          significance: item.avg_impact_score
        }));
        setChartData(formattedData);
      });
  }, [timeRange]);
  
  return (
    <div className="competitive-timeline">
      <h3>📈 Competitive Activity Timeline</h3>
      <div className="timeline-controls">
        <ButtonGroup>
          <Button onClick={() => setTimeRange('30d')}>30 Days</Button>
          <Button onClick={() => setTimeRange('90d')}>90 Days</Button>
          <Button onClick={() => setTimeRange('1y')}>1 Year</Button>
        </ButtonGroup>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          {competitors.map((competitor, index) => (
            <Line 
              key={competitor}
              type="monotone" 
              dataKey={`${competitor}_count`}
              stroke={COMPETITOR_COLORS[index]}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      
      <div className="trend-insights">
        {trendAlerts.map(alert => (
          <Alert key={alert.id} variant={alert.severity}>
            🚨 {alert.message}
          </Alert>
        ))}
      </div>
    </div>
  );
};
```

### 3.3 Backend APIs for Analysis

```python
@app.route('/api/competitive-analysis/matrix')
def competitive_matrix():
    """Generate feature comparison matrix across competitors."""
    # Query for recent updates by category and competitor
    matrix_data = db.session.query(
        Competitor.name,
        CompetitorUpdate.relevance_category,
        func.count(CompetitorUpdate.id).label('update_count'),
        func.max(CompetitorUpdate.approved_at).label('latest_update'),
        func.avg(CompetitorUpdate.impact_score).label('avg_impact')
    ).join(Competitor).filter(
        CompetitorUpdate.approved_at >= datetime.now() - timedelta(days=90),
        CompetitorUpdate.is_archived == False
    ).group_by(
        Competitor.name, 
        CompetitorUpdate.relevance_category
    ).all()
    
    # Transform into matrix format
    competitors = list(set(row.name for row in matrix_data))
    categories = list(set(row.relevance_category for row in matrix_data))
    
    matrix = {}
    for competitor in competitors:
        matrix[competitor] = {}
        for category in categories:
            # Find matching data
            match = next((row for row in matrix_data 
                         if row.name == competitor and row.relevance_category == category), None)
            if match:
                matrix[competitor][category] = {
                    'count': match.update_count,
                    'latest': match.latest_update,
                    'impact': round(match.avg_impact, 1),
                    'status': determine_feature_status(match)  # Helper function
                }
            else:
                matrix[competitor][category] = {'count': 0, 'status': 'none'}
    
    return jsonify({
        'competitors': competitors,
        'categories': categories,
        'matrix': matrix,
        'generated_at': datetime.now().isoformat()
    })

@app.route('/api/competitive-analysis/trends')
def trend_detection():
    """Detect spikes and trends in competitive intelligence."""
    
    # Query for recent activity patterns
    recent_activity = db.session.query(
        Competitor.name,
        CompetitorUpdate.relevance_category,
        func.date_trunc('week', CompetitorUpdate.approved_at).label('week'),
        func.count(CompetitorUpdate.id).label('weekly_count')
    ).join(Competitor).filter(
        CompetitorUpdate.approved_at >= datetime.now() - timedelta(days=90)
    ).group_by(
        Competitor.name, 
        CompetitorUpdate.relevance_category,
        func.date_trunc('week', CompetitorUpdate.approved_at)
    ).all()
    
    # Detect anomalies (simplified algorithm)
    trends = []
    for competitor in set(row.name for row in recent_activity):
        competitor_data = [row for row in recent_activity if row.name == competitor]
        
        # Calculate average weekly activity
        avg_weekly = sum(row.weekly_count for row in competitor_data) / len(competitor_data)
        
        # Find weeks with activity > 2x average
        for week_data in competitor_data:
            if week_data.weekly_count > avg_weekly * 2:
                trends.append({
                    'competitor': competitor,
                    'category': week_data.relevance_category,
                    'week': week_data.week,
                    'count': week_data.weekly_count,
                    'severity': 'high' if week_data.weekly_count > avg_weekly * 3 else 'medium',
                    'message': f"{competitor} had {week_data.weekly_count} {week_data.relevance_category} updates (vs. avg {avg_weekly:.1f})"
                })
    
    return jsonify({
        'trends': trends,
        'analysis_period': '90 days',
        'generated_at': datetime.now().isoformat()
    })
```

## 4. Proactive Alerts & Digests

### 4.1 Real-time Alert System

```python
# alerts.py - New module for alert management
from slack_sdk import WebClient
from flask import current_app
import smtplib
from email.mime.text import MimeText

class AlertManager:
    def __init__(self):
        self.slack_client = WebClient(token=current_app.config.get('SLACK_TOKEN'))
    
    def trigger_high_confidence_alert(self, update: CompetitorUpdate):
        """Send immediate alert for high-confidence, roadmap-relevant items."""
        if update.confidence_score > 80 and update.roadmap_theme:
            message = self._format_alert_message(update)
            
            # Send Slack notification
            self._send_slack_alert(message, update)
            
            # Send email to PMs
            self._send_email_alert(message, update)
    
    def _format_alert_message(self, update: CompetitorUpdate):
        return f"""
        🚨 HIGH-IMPACT COMPETITIVE INTEL
        
        Competitor: {update.competitor.name}
        Title: {update.title}
        Confidence: {update.confidence_score}%
        Roadmap Theme: {update.roadmap_theme}
        Impact Score: {update.impact_score}/100
        
        AI Summary: {update.ai_summary}
        
        Action Required: {update.action_item}
        
        View Details: {current_app.config['BASE_URL']}/update/{update.id}
        """
    
    def _send_slack_alert(self, message: str, update: CompetitorUpdate):
        """Send alert to designated Slack channel."""
        try:
            self.slack_client.chat_postMessage(
                channel=current_app.config.get('SLACK_ALERTS_CHANNEL', '#competitive-intel'),
                text=message,
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message}
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details"},
                                "url": f"{current_app.config['BASE_URL']}/update/{update.id}"
                            },
                            {
                                "type": "button", 
                                "text": {"type": "plain_text", "text": "Add to Roadmap"},
                                "url": f"{current_app.config['BASE_URL']}/roadmap?highlight={update.id}"
                            }
                        ]
                    }
                ]
            )
        except Exception as e:
            current_app.logger.error(f"Slack alert failed: {str(e)}")

# Add to main app routes
@app.route('/api/alerts/digest/weekly')
def generate_weekly_digest():
    """Generate and send weekly competitive intelligence digest."""
    
    week_start = datetime.now() - timedelta(days=7)
    
    # Get all approved updates from the past week
    weekly_updates = db.session.query(CompetitorUpdate, Competitor).join(
        Competitor
    ).filter(
        CompetitorUpdate.approved_at >= week_start,
        CompetitorUpdate.is_archived == False
    ).order_by(
        CompetitorUpdate.impact_score.desc()
    ).all()
    
    # Group by competitor and theme
    digest_data = {}
    for update, competitor in weekly_updates:
        if competitor.name not in digest_data:
            digest_data[competitor.name] = {'high_impact': [], 'medium_impact': [], 'themes': {}}
        
        # Categorize by impact
        if update.impact_score >= 80:
            digest_data[competitor.name]['high_impact'].append(update)
        else:
            digest_data[competitor.name]['medium_impact'].append(update)
        
        # Group by theme
        theme = update.roadmap_theme or 'Unthemed'
        if theme not in digest_data[competitor.name]['themes']:
            digest_data[competitor.name]['themes'][theme] = []
        digest_data[competitor.name]['themes'][theme].append(update)
    
    # Generate digest email
    digest_html = render_template('digest_email.html', 
                                 digest_data=digest_data,
                                 week_start=week_start,
                                 total_items=len(weekly_updates))
    
    # Send to all PMs
    pm_users = User.query.filter_by(role='product_manager', is_active=True).all()
    for pm in pm_users:
        send_digest_email(pm.email, digest_html)
    
    return jsonify({
        'success': True,
        'items_processed': len(weekly_updates),
        'recipients': len(pm_users),
        'digest_date': week_start.isoformat()
    })
```

### 4.2 Weekly Digest Email Template

```html
<!-- templates/digest_email.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        .digest-container { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: auto; }
        .header { background: #1976d2; color: white; padding: 20px; text-align: center; }
        .competitor-section { border-left: 4px solid #2196f3; margin: 20px 0; padding: 15px; }
        .high-impact { background: #ffebee; border-left-color: #f44336; }
        .medium-impact { background: #e3f2fd; border-left-color: #2196f3; }
        .theme-group { margin: 10px 0; padding: 10px; background: #f5f5f5; }
        .update-item { margin: 8px 0; padding: 8px; background: white; border-radius: 4px; }
        .confidence-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; color: white; }
        .confidence-high { background: #f44336; }
        .confidence-medium { background: #ff9800; }
    </style>
</head>
<body>
    <div class="digest-container">
        <div class="header">
            <h1>🎯 Weekly Competitive Intelligence Digest</h1>
            <p>{{ week_start.strftime('%B %d') }} - {{ (week_start + timedelta(days=7)).strftime('%B %d, %Y') }}</p>
            <p><strong>{{ total_items }}</strong> updates processed</p>
        </div>
        
        {% for competitor, data in digest_data.items() %}
        <div class="competitor-section">
            <h2>{{ competitor }}</h2>
            
            {% if data.high_impact %}
            <div class="high-impact">
                <h3>🔴 High Impact Updates</h3>
                {% for update in data.high_impact %}
                <div class="update-item">
                    <span class="confidence-badge confidence-high">{{ update.confidence_score }}%</span>
                    <strong>{{ update.title }}</strong><br>
                    <small>Theme: {{ update.roadmap_theme }} | Impact: {{ update.impact_score }}/100</small><br>
                    <p>{{ update.ai_summary }}</p>
                    {% if update.action_item %}
                    <div style="background: #fff3e0; padding: 5px; margin: 5px 0;">
                        <strong>Action:</strong> {{ update.action_item }}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if data.medium_impact %}
            <div class="medium-impact">
                <h3>🟡 Notable Updates</h3>
                {% for update in data.medium_impact %}
                <div class="update-item">
                    <span class="confidence-badge confidence-medium">{{ update.confidence_score }}%</span>
                    <strong>{{ update.title }}</strong><br>
                    <small>{{ update.roadmap_theme or 'General' }} | {{ update.published_date.strftime('%b %d') }}</small>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="theme-summary">
                <h4>📊 Activity by Theme:</h4>
                {% for theme, updates in data.themes.items() %}
                <span style="display: inline-block; margin: 4px; padding: 4px 8px; background: #e1f5fe; border-radius: 4px;">
                    {{ theme }}: {{ updates|length }}
                </span>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ config.BASE_URL }}/roadmap" 
               style="background: #1976d2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                View Full Roadmap Dashboard →
            </a>
        </div>
    </div>
</body>
</html>
```

## 5. LLM-Powered Summarization Hook

### 5.1 AI Summarization Service

```python
# ai_summarization.py - Enhanced service
import openai
from celery import Celery
from flask import current_app
from datetime import datetime

# Configure Celery for background tasks
celery = Celery('competitive_intel')

@celery.task(bind=True, max_retries=3)
def generate_ai_summary(self, competitor_update_id):
    """Generate AI summary for approved competitive intelligence item."""
    try:
        # Get the update record
        update = CompetitorUpdate.query.get(competitor_update_id)
        if not update:
            return {'error': 'Update not found'}
        
        # Get the original raw content
        raw_item = update.raw_fetch
        content = raw_item.content or ''
        title = update.title or ''
        
        # Prepare context for better summarization
        context = {
            'competitor': update.competitor.name,
            'title': title,
            'category': update.relevance_category,
            'roadmap_theme': update.roadmap_theme,
            'confidence_score': float(update.confidence_score)
        }
        
        # Generate summary using OpenAI
        summary = generate_competitive_summary(content, context)
        
        # Update the record
        update.ai_summary = summary
        update.updated_at = datetime.now()
        db.session.commit()
        
        # Trigger alert if high-impact
        if update.confidence_score > 80 and update.roadmap_theme:
            AlertManager().trigger_high_confidence_alert(update)
        
        return {
            'success': True,
            'summary': summary,
            'update_id': competitor_update_id
        }
        
    except Exception as e:
        # Retry logic
        if self.request.retries < self.max_retries:
            current_app.logger.warning(f"AI summarization failed, retrying: {str(e)}")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        else:
            current_app.logger.error(f"AI summarization failed permanently: {str(e)}")
            return {'error': str(e)}

def generate_competitive_summary(content: str, context: dict) -> str:
    """Generate focused competitive intelligence summary using OpenAI."""
    
    # Construct prompt for PM-focused analysis
    prompt = f"""
    Analyze the following competitive intelligence about {context['competitor']} and provide a concise summary for product managers.
    
    Context:
    - Competitor: {context['competitor']}
    - Category: {context.get('category', 'Unknown')}
    - Roadmap Theme: {context.get('roadmap_theme', 'General')}
    - Confidence: {context['confidence_score']}%
    
    Content to analyze:
    {content[:2000]}  # Truncate for token limits
    
    Provide a summary that answers:
    1. What exactly did they announce/launch?
    2. What's the competitive impact or threat level?
    3. What should our product team consider?
    
    Keep it to 2-3 sentences maximum. Be specific and actionable.
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a competitive intelligence analyst for a product team. Provide concise, actionable summaries focused on product strategy implications."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3  # Lower temperature for more focused summaries
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        current_app.logger.error(f"OpenAI API error: {str(e)}")
        return f"AI summarization temporarily unavailable. Manual review recommended for {context['competitor']} update."

# Integration hook in main app
@app.route('/api/summarize/<uuid:update_id>', methods=['POST'])
def trigger_summarization(update_id):
    """Manually trigger AI summarization for an update."""
    
    update = CompetitorUpdate.query.get_or_404(update_id)
    
    # Queue background task
    task = generate_ai_summary.delay(str(update_id))
    
    return jsonify({
        'success': True,
        'task_id': task.id,
        'message': 'AI summarization queued'
    })

@app.route('/api/summarize/batch', methods=['POST'])
def batch_summarize():
    """Batch process items without AI summaries."""
    
    # Find updates without AI summaries
    pending_updates = CompetitorUpdate.query.filter(
        CompetitorUpdate.ai_summary.is_(None),
        CompetitorUpdate.is_archived == False
    ).limit(50).all()  # Process in batches to avoid overwhelming API
    
    tasks = []
    for update in pending_updates:
        task = generate_ai_summary.delay(str(update.id))
        tasks.append(task.id)
    
    return jsonify({
        'success': True,
        'queued_tasks': len(tasks),
        'task_ids': tasks
    })
```

### 5.2 Sample LLM Integration Code

```python
# Example usage in scraper integration
def enhance_raw_item_with_ai(raw_item: RawFetchQueue):
    """Add AI-enhanced metadata to raw scraped items."""
    
    if not raw_item.content:
        return
    
    try:
        # Quick classification using LLM
        classification_result = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"""
                Classify this content from {raw_item.competitor.name}:
                
                Title: {raw_item.title}
                Content: {raw_item.content[:1000]}
                
                Provide:
                1. Category (product_launch, partnership, strategy, acquisition, funding, other)
                2. Confidence score 0-100 for competitive relevance
                3. One-sentence summary
                
                Format as JSON: {{"category": "", "confidence": 0, "summary": ""}}
                """
            }],
            max_tokens=100,
            temperature=0.2
        )
        
        result = json.loads(classification_result.choices[0].message.content)
        
        # Update raw item with AI insights
        raw_item.meta_info.update({
            'ai_category': result.get('category'),
            'ai_confidence_boost': result.get('confidence', 0),
            'ai_quick_summary': result.get('summary'),
            'ai_processed_at': datetime.now().isoformat()
        })
        
        # Adjust confidence score if AI suggests higher relevance
        if result.get('confidence', 0) > raw_item.confidence_score:
            raw_item.confidence_score = min(result['confidence'], 100.0)
        
    except Exception as e:
        logger.warning(f"AI enhancement failed for {raw_item.id}: {str(e)}")
        raw_item.meta_info.update({
            'ai_error': str(e),
            'ai_processed_at': datetime.now().isoformat()
        })
```

## 6. UI/UX & PM Lens

### 6.1 Keyboard Shortcuts & Fast Navigation

```javascript
// shortcuts.js - Keyboard navigation for power users
const KeyboardShortcuts = {
  init() {
    document.addEventListener('keydown', this.handleKeyPress.bind(this));
    this.currentItemIndex = 0;
    this.items = document.querySelectorAll('.triage-card');
  },
  
  handleKeyPress(event) {
    // Only handle shortcuts when not typing in inputs
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
      return;
    }
    
    switch(event.key) {
      case 'j': // Next item
        this.navigateItem(1);
        break;
      case 'k': // Previous item  
        this.navigateItem(-1);
        break;
      case 'a': // Approve current item
        this.performAction('approve');
        break;
      case 'r': // Reject current item
        this.performAction('reject');
        break;
      case 'x': // Archive current item
        this.performAction('archive');
        break;
      case '1': // Mark as roadmap relevant
        this.performAction('roadmap_relevant');
        break;
      case '2': // Mark as pricing/ignore
        this.performAction('pricing');
        break;
      case '3': // Mark as need more info
        this.performAction('need_info');
        break;
      case 'h': // Show help
        this.showShortcutHelp();
        break;
      case 'Escape': // Clear selection
        this.clearHighlight();
        break;
    }
  },
  
  navigateItem(direction) {
    this.clearHighlight();
    this.currentItemIndex = Math.max(0, Math.min(
      this.items.length - 1, 
      this.currentItemIndex + direction
    ));
    
    const currentItem = this.items[this.currentItemIndex];
    currentItem.classList.add('keyboard-selected');
    currentItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
  },
  
  performAction(action) {
    const currentItem = this.items[this.currentItemIndex];
    if (!currentItem) return;
    
    const itemId = currentItem.dataset.itemId;
    const actionButton = currentItem.querySelector(`[data-action="${action}"]`);
    
    if (actionButton) {
      actionButton.click();
    } else {
      // Handle programmatically
      this.executeAction(itemId, action);
    }
  },
  
  showShortcutHelp() {
    const helpModal = `
      <div class="shortcut-help-modal">
        <h3>⌨️ Keyboard Shortcuts</h3>
        <div class="shortcut-grid">
          <div><kbd>j</kbd> Next item</div>
          <div><kbd>k</kbd> Previous item</div>
          <div><kbd>a</kbd> Approve</div>
          <div><kbd>r</kbd> Reject</div>
          <div><kbd>x</kbd> Archive</div>
          <div><kbd>1</kbd> Roadmap relevant</div>
          <div><kbd>2</kbd> Pricing/ignore</div>
          <div><kbd>3</kbd> Need info</div>
          <div><kbd>h</kbd> Show this help</div>
          <div><kbd>Esc</kbd> Clear selection</div>
        </div>
        <button onclick="this.parentElement.remove()">Close</button>
      </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', helpModal);
  }
};
```

### 6.2 Responsive Layout CSS

```css
/* competitive-intel.css - PM-focused design system */
:root {
  --confidence-high: #f44336;
  --confidence-medium: #ff9800;  
  --confidence-low: #9e9e9e;
  --roadmap-color: #1976d2;
  --success-color: #4caf50;
  --warning-color: #ff9800;
  --spacing-unit: 8px;
}

.dashboard-container {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: calc(var(--spacing-unit) * 3);
  padding: calc(var(--spacing-unit) * 3);
  min-height: 100vh;
}

.triage-queue {
  display: flex;
  flex-direction: column;
  gap: calc(var(--spacing-unit) * 2);
}

.triage-card {
  border: 1px solid #e0e0e0;
  border-radius: calc(var(--spacing-unit));
  background: white;
  transition: all 0.2s ease;
  position: relative;
}

.triage-card.keyboard-selected {
  box-shadow: 0 0 0 3px var(--roadmap-color);
  transform: translateY(-2px);
}

.triage-card.high-confidence { 
  border-left: 4px solid var(--confidence-high); 
}
.triage-card.medium-confidence { 
  border-left: 4px solid var(--confidence-medium); 
}
.triage-card.low-confidence { 
  border-left: 4px solid var(--confidence-low); 
}

.confidence-badge {
  position: absolute;
  top: calc(var(--spacing-unit) * 2);
  right: calc(var(--spacing-unit) * 2);
  background: var(--confidence-high);
  color: white;
  padding: calc(var(--spacing-unit)) calc(var(--spacing-unit) * 2);
  border-radius: 20px;
  font-weight: bold;
  font-size: 14px;
}

.confidence-badge.medium { background: var(--confidence-medium); }
.confidence-badge.low { background: var(--confidence-low); }

.card-header {
  padding: calc(var(--spacing-unit) * 3);
  border-bottom: 1px solid #f0f0f0;
}

.card-header h3 {
  margin: 0 0 calc(var(--spacing-unit)) 0;
  color: #333;
  font-size: 18px;
}

.card-header a {
  color: var(--roadmap-color);
  text-decoration: none;
  font-weight: 500;
}

.meta-row {
  display: flex;
  gap: calc(var(--spacing-unit) * 2);
  color: #666;
  font-size: 14px;
  margin-top: calc(var(--spacing-unit));
}

.ai-summary {
  background: #f8f9fa;
  padding: calc(var(--spacing-unit) * 2);
  border-radius: calc(var(--spacing-unit));
  margin: calc(var(--spacing-unit) * 2) 0;
  border-left: 3px solid #17a2b8;
  font-style: italic;
}

.quick-actions {
  display: flex;
  gap: calc(var(--spacing-unit));
  margin: calc(var(--spacing-unit) * 2) 0;
  flex-wrap: wrap;
}

.quick-action-btn {
  padding: calc(var(--spacing-unit)) calc(var(--spacing-unit) * 2);
  border: 1px solid #ddd;
  border-radius: calc(var(--spacing-unit));
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.quick-action-btn.roadmap { 
  background: var(--roadmap-color); 
  color: white; 
  border-color: var(--roadmap-color); 
}

.quick-action-btn.pricing { 
  background: var(--warning-color); 
  color: white; 
  border-color: var(--warning-color); 
}

.quick-action-btn.info { 
  background: #17a2b8; 
  color: white; 
  border-color: #17a2b8; 
}

.detailed-fields {
  background: #fafafa;
  padding: calc(var(--spacing-unit) * 2);
  border-radius: calc(var(--spacing-unit));
  margin-top: calc(var(--spacing-unit) * 2);
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(var(--spacing-unit) * 2);
  margin-bottom: calc(var(--spacing-unit) * 2);
}

.action-buttons {
  display: flex;
  gap: calc(var(--spacing-unit));
  padding: calc(var(--spacing-unit) * 2);
  border-top: 1px solid #f0f0f0;
  justify-content: flex-end;
}

.btn-primary {
  background: var(--success-color);
  color: white;
  border: none;
  padding: calc(var(--spacing-unit) * 1.5) calc(var(--spacing-unit) * 3);
  border-radius: calc(var(--spacing-unit));
  cursor: pointer;
  font-weight: 500;
}

.sidebar {
  background: white;
  border-radius: calc(var(--spacing-unit));
  padding: calc(var(--spacing-unit) * 3);
  height: fit-content;
  position: sticky;
  top: calc(var(--spacing-unit) * 3);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(var(--spacing-unit) * 2);
  margin-bottom: calc(var(--spacing-unit) * 3);
}

.stat-card {
  text-align: center;
  padding: calc(var(--spacing-unit) * 2);
  border-radius: calc(var(--spacing-unit));
  background: #f8f9fa;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: var(--roadmap-color);
}

/* Responsive design for tablet/mobile */
@media (max-width: 1024px) {
  .dashboard-container {
    grid-template-columns: 1fr;
    gap: calc(var(--spacing-unit) * 2);
    padding: calc(var(--spacing-unit) * 2);
  }
  
  .sidebar {
    position: static;
    order: -1;
  }
  
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  
  .field-row {
    grid-template-columns: 1fr;
  }
  
  .quick-actions {
    justify-content: center;
  }
  
  .action-buttons {
    justify-content: stretch;
  }
  
  .action-buttons button {
    flex: 1;
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .confidence-badge {
    position: static;
    display: inline-block;
    margin-left: calc(var(--spacing-unit) * 2);
  }
  
  .meta-row {
    flex-direction: column;
    gap: calc(var(--spacing-unit));
  }
}
```

## 7. Implementation Priority & Scope

### 7.1 Phase 1 (MVP) - 2 weeks
1. **Enhanced Triage Interface**
   - Upgrade existing triage cards with confidence badges
   - Add AI summary field display
   - Implement quick action buttons
   - Basic category tagging

2. **AI Summarization Integration**
   - OpenAI API integration for summary generation
   - Background task queue with Celery
   - Batch processing endpoint

3. **Basic Roadmap Routing**
   - Simple theme dropdown in triage
   - Route approved items to themes
   - Basic roadmap dashboard showing themes and counts

### 7.2 Phase 2 (Enhanced) - 3 weeks
1. **Comparative Analysis Views**
   - Feature matrix API and UI
   - Timeline chart with basic trend detection
   - Competitor activity dashboard

2. **Alert System**
   - High-confidence item Slack/email alerts
   - Weekly digest generation and sending
   - Configurable alert thresholds

3. **UI Polish**
   - Keyboard shortcuts for power users
   - Responsive design implementation
   - Enhanced filtering and search

### 7.3 Phase 3 (Advanced) - 2 weeks
1. **Advanced Analytics**
   - Trend anomaly detection
   - Impact vs. urgency matrix
   - Competitive positioning insights

2. **Workflow Optimization**
   - Bulk triage operations
   - Smart categorization suggestions
   - Advanced roadmap integration with OKRs

### 7.4 Data Model Migration Script

```sql
-- Phase 1 Migration Script
-- Add roadmapping fields to existing competitor_updates table
ALTER TABLE competitor_updates 
ADD COLUMN roadmap_theme VARCHAR(100),
ADD COLUMN action_item TEXT,
ADD COLUMN impact_score INTEGER DEFAULT 50 CHECK (impact_score >= 0 AND impact_score <= 100);

-- Create roadmap themes table
CREATE TABLE roadmap_themes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    color_hex VARCHAR(7) DEFAULT '#2196F3',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Add indexes for performance
CREATE INDEX idx_competitor_updates_theme ON competitor_updates(roadmap_theme);
CREATE INDEX idx_competitor_updates_impact ON competitor_updates(impact_score DESC);

-- Insert default themes
INSERT INTO roadmap_themes (name, description, color_hex) VALUES
('Data Platform', 'Core data infrastructure and storage capabilities', '#1976D2'),
('AI/ML Engine', 'Machine learning and artificial intelligence features', '#9C27B0'),
('Security & Compliance', 'Security, privacy, and regulatory compliance', '#F44336'),
('User Experience', 'Interface, usability, and user-facing features', '#4CAF50'),
('Performance & Scale', 'System performance and scalability improvements', '#FF9800'),
('Integration & APIs', 'Third-party integrations and API capabilities', '#00BCD4'),
('Business Intelligence', 'Analytics, reporting, and business insights', '#795548');

-- Update existing records with sample themes (optional)
UPDATE competitor_updates 
SET roadmap_theme = CASE 
    WHEN relevance_category = 'product_launch' THEN 'Data Platform'
    WHEN relevance_category = 'partnership' THEN 'Integration & APIs'
    WHEN relevance_category = 'strategy' THEN 'Business Intelligence'
    ELSE 'Data Platform'
END
WHERE roadmap_theme IS NULL AND relevance_category IS NOT NULL;
```

## Conclusion

This specification provides a comprehensive roadmap for transforming the existing competitive intelligence scraper into a full PM-focused dashboard. The design prioritizes:

- **Speed**: Keyboard shortcuts and bulk operations for efficient triage
- **Intelligence**: AI-powered summarization and confidence scoring
- **Insight**: Comparative analysis and trend detection for strategic decisions
- **Integration**: Seamless roadmap planning and OKR alignment
- **Actionability**: Clear next steps and impact assessment for each intelligence item

The modular implementation approach allows for incremental delivery while maintaining the existing system's stability and functionality.
