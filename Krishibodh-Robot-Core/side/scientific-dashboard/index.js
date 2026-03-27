const express = require('express');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http);
const path = require('path');
const fs = require('fs');

// Middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// View Engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Routes
app.get('/', (req, res) => {
    res.render('selection');
});

// Socket.io
io.on('connection', (socket) => {
    console.log('Client connected');

    socket.on('protocol_selected', (data) => {
        console.log('Protocol selected:', data);
        // Be generous with logging
        fs.appendFile('dashboard_logs.txt', `${new Date().toISOString()}: Protocol selected - ${JSON.stringify(data)}\n`, (err) => {
            if (err) console.error('Error logging:', err);
        });
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected');
    });
});

const PORT = 3000;
http.listen(PORT, () => {
    console.log(`Scientific Dashboard running on http://localhost:${PORT}`);
});
