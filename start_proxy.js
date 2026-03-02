const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = 8000;
const PROD_API_BASE = 'https://store-tracker-prod.bounceme.net';

const server = http.createServer((req, res) => {
    // 1. API Reverse Proxy Router
    if (req.url.startsWith('/api/')) {
        console.log(`[PROXY] Forwarding ${req.method} ${req.url}`);

        const options = {
            hostname: url.parse(PROD_API_BASE).hostname,
            path: req.url,
            method: req.method,
            headers: {
                ...req.headers,
                host: url.parse(PROD_API_BASE).hostname,
            }
        };

        const proxyReq = https.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res, { end: true });
        });

        proxyReq.on('error', (e) => {
            console.error(`[PROXY ERROR] ${e.message}`);
            res.writeHead(500);
            res.end(`Proxy Error: ${e.message}`);
        });

        req.pipe(proxyReq, { end: true });
        return;
    }

    // 2. Static File Server Router
    let filePath = '.' + req.url;
    if (filePath === './') {
        filePath = './index.html';
    }

    const extname = String(path.extname(filePath)).toLowerCase();
    const mimeTypes = {
        '.html': 'text/html',
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
    };

    const contentType = mimeTypes[extname] || 'application/octet-stream';

    fs.readFile(filePath, (error, content) => {
        if (error) {
            if (error.code === 'ENOENT') {
                console.log(`[GET] 404 ${filePath}`);
                res.writeHead(404);
                res.end('File not found');
            } else {
                console.log(`[GET] 500 ${filePath}`);
                res.writeHead(500);
                res.end(`Server Error: ${error.code}`);
            }
        } else {
            console.log(`[GET] 200 ${filePath}`);
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

server.listen(PORT, () => {
    console.log(`===============================================`);
    console.log(`🚀 Store Tracker Local Dev Proxy Started!`);
    console.log(`===============================================`);
    console.log(`📱 Local App URL: http://localhost:${PORT}`);
    console.log(`🔄 API Proxying to: ${PROD_API_BASE}`);
    console.log(`===============================================`);
});
