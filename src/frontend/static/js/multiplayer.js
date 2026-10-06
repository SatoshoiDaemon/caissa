class MultiplayerHandler {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.socket = null;
        this.roomCode = null;
        this.isConnected = false;
        this.isSpectator = false;
        this.spectatorToken = null;
        this.hasConnected = false;
        this.manualDisconnect = false;
        this.lastEndedVersion = null;
    }

    connect() {
        this.socket = io();

        this.socket.on('connect', () => {
            this.isConnected = true;
            const reconnect = this.hasConnected;
            this.hasConnected = true;
            this.setConnectionStatus(reconnect ? 'Reconectado' : 'Conectado', reconnect ? 'reconnected' : 'connected');
            if (reconnect) this.gameClient.notify('Conexão restaurada. Estado sincronizado.', 'success');
            if (this.roomCode && this.gameClient.gameId) {
                if (this.isSpectator && this.spectatorToken) this.spectateRoom(this.roomCode, this.gameClient.gameId, this.spectatorToken);
                else if (this.gameClient.playerToken) this.joinRoom(this.roomCode, this.gameClient.gameId, this.gameClient.playerToken);
            }
        });

        this.socket.on('disconnect', () => {
            this.isConnected = false;
            if (!this.manualDisconnect) {
                this.setConnectionStatus('Conexão perdida', 'lost');
                this.gameClient.notify('Conexão perdida. Tentando reconectar…', 'error');
            }
            this.manualDisconnect = false;
        });

        this.socket.on('connect_error', (error) => {
            const expired = /auth|unauthori|forbidden|session/i.test(error?.message || '');
            this.setConnectionStatus(expired ? 'Sessão expirada' : 'Sem conexão', expired ? 'expired' : 'lost');
            this.gameClient.notify(expired ? 'Sua sessão expirou. Entre novamente.' : 'Não foi possível conectar ao servidor.', 'error');
        });

        this.socket.on('player_joined', (data) => {
            this.gameClient.notify(`${data.player_name} entrou como ${data.player_color}.`, 'success');
        });

        this.socket.on('move_made', (data) => {
            this.gameClient.applyGameState(data.game_state);
        });

        this.socket.on('draw_offered', () => {
            if (this.isSpectator) return;
            this.gameClient.requestConfirmation('Oferta de empate', 'O oponente ofereceu empate. Aceitar encerra a partida.', 'Aceitar empate')
                .then((accepted) => { if (accepted) this.acceptDraw(); else this.declineDraw(); });
        });

        this.socket.on('draw_accepted', () => {
            this.gameClient.notify('Oponente aceitou o empate.', 'success');
            this.gameClient.finish('draw', null);
        });

        this.socket.on('game_ended', (data) => {
            const state = data.game_state;
            if (!state) return;
            const version = state.version ?? null;
            if (version !== null && this.lastEndedVersion === version) return;
            this.lastEndedVersion = version;
            this.gameClient.applyGameState(state);
            const winner = state.status === 'draw' || state.status === 'stalemate' ? 'draw' : state.winner;
            this.gameClient.finish(winner, data.reason || state.status || 'Partida encerrada');
        });

        this.socket.on('server_error', (data) => {
            console.error('Server error:', data.message);
            this.gameClient.notify(data.error || data.message || 'O servidor rejeitou a ação.', 'error');
        });

        this.socket.on('draw_declined', () => this.gameClient.notify('A oferta de empate foi recusada.', 'info'));
        this.socket.on('player_disconnected', (data) => {
            this.gameClient.notify(`Jogador ${data.player_color} desconectado. Reconexão disponível por ${data.reconnect_grace_seconds}s.`, 'info');
            if (data.player_color !== this.gameClient.playerColor) this.gameClient.setOpponentStatus(`Oponente desconectado · reconexão em até ${data.reconnect_grace_seconds}s`);
        });
        this.socket.on('player_reconnected', (data) => {
            this.gameClient.notify(`Jogador ${data.player_color} reconectado.`, 'success');
            if (data.player_color !== this.gameClient.playerColor) this.gameClient.setOpponentStatus('Oponente reconectado');
        });

        this.socket.on('room_state', (data) => {
            if (!data.game_state) return;
            this.gameClient.applyGameState(data.game_state);
        });

        this.socket.on('clock_updated', (data) => {
            if (data.game_state) {
                this.gameClient.applyGameState(data.game_state);
            }
        });
    }

    setConnectionStatus(label, state) {
        window.uiHandler?.setConnectionStatus(label, state);
    }

    joinRoom(roomCode, gameId, playerToken) {
        this.roomCode = roomCode;
        this.isSpectator = false;
        
        this.socket.emit('join_room', {
            room_code: roomCode,
            game_id: gameId,
            player_token: playerToken
        });
    }

    spectateRoom(roomCode, gameId, spectatorToken) {
        this.roomCode = roomCode;
        this.isSpectator = true;
        this.spectatorToken = spectatorToken;
        this.socket.emit('spectate_room', { room_code: roomCode, game_id: gameId, spectator_token: spectatorToken });
    }

    makeMove(fromPos, toPos, promotion = null) {
        if (this.isSpectator) return;
        if (!this.isConnected) {
            console.error('Not connected to server');
            return;
        }

        this.socket.emit('make_move', {
            room_code: this.roomCode,
            game_id: this.gameClient.gameId,
            player_token: this.gameClient.playerToken,
            event_id: crypto.randomUUID(),
            move: {
                from: fromPos,
                to: toPos,
                ...(promotion ? { promotion } : {})
            }
        });
    }

    offerDraw() {
        if (!this.isConnected || this.isSpectator) return;

        this.socket.emit('offer_draw', {
            room_code: this.roomCode,
            game_id: this.gameClient.gameId,
            player_token: this.gameClient.playerToken,
            event_id: crypto.randomUUID()
        });
    }

    acceptDraw() {
        if (!this.isConnected || this.isSpectator) return;

        this.socket.emit('accept_draw', {
            room_code: this.roomCode,
            game_id: this.gameClient.gameId,
            player_token: this.gameClient.playerToken,
            event_id: crypto.randomUUID()
        });
    }

    resign() {
        if (!this.isConnected || this.isSpectator) return;

        this.socket.emit('resign_game', {
            room_code: this.roomCode,
            game_id: this.gameClient.gameId,
            player_token: this.gameClient.playerToken,
            event_id: crypto.randomUUID()
        });
    }

    declineDraw() {
        if (!this.isConnected || this.isSpectator) return;
        this.socket.emit('decline_draw', {
            room_code: this.roomCode,
            game_id: this.gameClient.gameId,
            player_token: this.gameClient.playerToken,
            event_id: crypto.randomUUID()
        });
    }

    disconnect() {
        if (this.socket) {
            this.manualDisconnect = true;
            this.socket.disconnect();
        }
    }

    retry() {
        if (this.socket) {
            this.manualDisconnect = true;
            this.socket.disconnect();
        }
        this.connect();
    }
}

// Global instance to be used with the game
let multiplayerHandler = null;

document.addEventListener('DOMContentLoaded', () => {
    // Multiplayer handler will be initialized when needed
});
