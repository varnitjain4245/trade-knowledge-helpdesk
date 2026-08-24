const http = require('http');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const PORT = 4200;
const HOST = '127.0.0.1';

// Resolve project root (assumes server.js is at <project>/.ai/dashboard/server.js)
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const AI_DIR = path.join(PROJECT_ROOT, '.ai');
const PUBLIC_DIR = path.join(__dirname, 'public');

// Auto-detect conversation ID by finding the transcript log
function findTranscriptPath() {
  const brainDir = path.join(
    process.env.HOME || process.env.USERPROFILE || '',
    '.gemini', 'antigravity', 'brain'
  );
  if (!fs.existsSync(brainDir)) return null;
  
  const conversations = fs.readdirSync(brainDir).filter(d => {
    const logPath = path.join(brainDir, d, '.system_generated', 'logs', 'transcript.jsonl');
    return fs.existsSync(logPath);
  });
  
  if (conversations.length === 0) return null;
  
  // Pick the most recently modified transcript
  let latest = null;
  let latestMtime = 0;
  for (const conv of conversations) {
    const logPath = path.join(brainDir, conv, '.system_generated', 'logs', 'transcript.jsonl');
    try {
      const stat = fs.statSync(logPath);
      if (stat.mtimeMs > latestMtime) {
        latestMtime = stat.mtimeMs;
        latest = logPath;
      }
    } catch (e) { /* skip */ }
  }
  return latest;
}

// MIME types
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
};

// Serve static file
function serveStatic(res, filePath) {
  const ext = path.extname(filePath);
  const mime = MIME[ext] || 'text/plain; charset=utf-8';
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    res.writeHead(200, { 'Content-Type': mime });
    res.end(content);
  } catch (e) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
}

// API: Return project state
function handleState(req, res) {
  const statePath = path.join(AI_DIR, 'state', 'project.json');
  try {
    const data = fs.readFileSync(statePath, 'utf-8');
    JSON.parse(data); // Validate JSON
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' });
    res.end(data);
  } catch (e) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'not_started', error: e.message }));
  }
}

// API: Parse transcript JSONL for real metrics
async function handleMetrics(req, res) {
  const transcriptPath = findTranscriptPath();
  
  if (!transcriptPath || !fs.existsSync(transcriptPath)) {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' });
    res.end(JSON.stringify({
      total_lines: 0, planner_responses: 0, tool_calls: 0,
      code_edits: 0, commands_run: 0, user_inputs: 0, errors: 0,
      questions_asked: 0, first_timestamp: null, last_timestamp: null,
      elapsed_seconds: 0, step_types: {}, content_bytes: {}
    }));
    return;
  }

  const metrics = {
    total_lines: 0,
    planner_responses: 0,
    tool_calls: 0,
    code_edits: 0,
    commands_run: 0,
    user_inputs: 0,
    errors: 0,
    questions_asked: 0,
    view_files: 0,
    grep_searches: 0,
    list_dirs: 0,
    checkpoints: 0,
    first_timestamp: null,
    last_timestamp: null,
    elapsed_seconds: 0,
    step_types: {},
    content_bytes: {},
    parse_errors: 0
  };

  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: fs.createReadStream(transcriptPath),
      crlfDelay: Infinity
    });

    rl.on('line', (line) => {
      metrics.total_lines++;
      try {
        const record = JSON.parse(line);
        const type = record.type || 'UNKNOWN';
        
        metrics.step_types[type] = (metrics.step_types[type] || 0) + 1;

        // Track timestamps
        if (record.created_at) {
          if (!metrics.first_timestamp) metrics.first_timestamp = record.created_at;
          metrics.last_timestamp = record.created_at;
        }

        // Count by type
        if (type === 'PLANNER_RESPONSE') {
          metrics.planner_responses++;
          const calls = record.tool_calls || [];
          metrics.tool_calls += calls.length;
        }
        if (type === 'CODE_ACTION') metrics.code_edits++;
        if (type === 'RUN_COMMAND') metrics.commands_run++;
        if (type === 'USER_INPUT') metrics.user_inputs++;
        if (type === 'ERROR_MESSAGE') metrics.errors++;
        if (type === 'ASK_QUESTION') metrics.questions_asked++;
        if (type === 'VIEW_FILE') metrics.view_files++;
        if (type === 'GREP_SEARCH') metrics.grep_searches++;
        if (type === 'LIST_DIRECTORY') metrics.list_dirs++;
        if (type === 'CHECKPOINT') metrics.checkpoints++;

        // Content byte sizes
        if (record.content) {
          const bytes = Buffer.byteLength(record.content, 'utf8');
          metrics.content_bytes[type] = (metrics.content_bytes[type] || 0) + bytes;
        }
      } catch (e) {
        metrics.parse_errors++;
      }
    });

    rl.on('close', () => {
      // Compute elapsed
      if (metrics.first_timestamp && metrics.last_timestamp) {
        const first = new Date(metrics.first_timestamp).getTime();
        const last = new Date(metrics.last_timestamp).getTime();
        metrics.elapsed_seconds = Math.round((last - first) / 1000);
      }
      
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' });
      res.end(JSON.stringify(metrics));
      resolve();
    });

    rl.on('error', () => {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Failed to parse transcript' }));
      resolve();
    });
  });
}

// API: Read artifact .md file
function handleArtifact(req, res) {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const artifactPath = url.searchParams.get('path');
  
  if (!artifactPath) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    res.end('Missing ?path= parameter');
    return;
  }

  // Security: prevent directory traversal
  if (artifactPath.includes('..')) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('Forbidden: path traversal detected');
    return;
  }

  const fullPath = path.join(PROJECT_ROOT, artifactPath);
  
  try {
    const content = fs.readFileSync(fullPath, 'utf-8');
    res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-cache' });
    res.end(content);
  } catch (e) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end(`Artifact not found: ${artifactPath}`);
  }
}

// Main server
const server = http.createServer(async (req, res) => {
  // CORS headers for local dev
  res.setHeader('Access-Control-Allow-Origin', '*');
  
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const pathname = url.pathname;

  // API routes
  if (pathname === '/api/state') return handleState(req, res);
  if (pathname === '/api/metrics') return handleMetrics(req, res);
  if (pathname === '/api/artifact') return handleArtifact(req, res);

  // Static files
  if (pathname === '/' || pathname === '/index.html') {
    return serveStatic(res, path.join(PUBLIC_DIR, 'index.html'));
  }
  if (pathname === '/style.css') {
    return serveStatic(res, path.join(PUBLIC_DIR, 'style.css'));
  }
  if (pathname === '/app.js') {
    return serveStatic(res, path.join(PUBLIC_DIR, 'app.js'));
  }

  // Fallback
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

server.listen(PORT, HOST, () => {
  console.log(`\n  ╔══════════════════════════════════════════════════╗`);
  console.log(`  ║  🚀 Workflow Dashboard running at               ║`);
  console.log(`  ║  → http://${HOST}:${PORT}                     ║`);
  console.log(`  ║                                                  ║`);
  console.log(`  ║  Real-time SDLC pipeline monitor                 ║`);
  console.log(`  ║  Auto-refresh: every 2 seconds                   ║`);
  console.log(`  ╚══════════════════════════════════════════════════╝\n`);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\n  ❌ Port ${PORT} is already in use. Try: kill -9 $(lsof -ti:${PORT})\n`);
  } else {
    console.error('Server error:', err);
  }
  process.exit(1);
});
