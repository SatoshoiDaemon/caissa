class ChessBoard {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.squares = new Map();
        this.selectedSquare = null;
        this.highlightedSquares = new Set();
        this.focusedSquare = 'a8';
        this.previousBoardState = null;
        this.pieceSymbols = {
            p: '♟',
            r: '♜',
            n: '♞',
            b: '♝',
            q: '♛',
            k: '♚'
        };
    }

    initialize() {
        this.container.innerHTML = '';
        this.squares.clear();

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const square = document.createElement('button');
                const pos = this.rowColToPos(row, col);
                
                square.type = 'button';
                square.className = 'square';
                square.classList.add((row + col) % 2 === 0 ? 'light' : 'dark');
                square.dataset.pos = pos;
                square.tabIndex = pos === this.focusedSquare ? 0 : -1;
                square.setAttribute('aria-label', `Casa ${pos}, vazia`);
                square.addEventListener('click', () => {
                    this.focusSquare(pos, false);
                    this.onSquareClickCallback?.(pos);
                });
                square.addEventListener('keydown', (event) => this.handleKeydown(event, pos));

                this.container.appendChild(square);
                this.squares.set(pos, square);
            }
        }
        this.container.setAttribute('role', 'grid');
        this.container.setAttribute('aria-label', 'Tabuleiro de xadrez');
    }

    rowColToPos(row, col) {
        return String.fromCharCode(97 + col) + (8 - row);
    }

    posToRowCol(pos) {
        const col = pos.charCodeAt(0) - 97;
        const row = 8 - parseInt(pos[1]);
        return { row, col };
    }

    updateBoard(boardState) {
        const previousBoard = this.previousBoardState;
        this.clearPieces();

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const piece = boardState[row][col];
                if (piece) {
                    const pos = this.rowColToPos(row, col);
                    const oldPiece = previousBoard?.[row]?.[col] || null;
                    const changed = !oldPiece || oldPiece.type !== piece.type || oldPiece.color !== piece.color;
                    this.setPiece(pos, piece, changed && Boolean(previousBoard));
                }
            }
        }
        this.previousBoardState = boardState.map((row) => row.map((piece) => piece ? { ...piece } : null));
        const focused = this.squares.get(this.focusedSquare);
        if (focused) focused.focus({ preventScroll: true });
    }

    setPiece(pos, piece, animate = false) {
        if (!piece) return;
        
        const square = this.squares.get(pos);
        if (!square) return;

        const pieceElement = document.createElement('span');
        pieceElement.className = 'piece';
        if (animate) pieceElement.classList.add('piece-arriving');
        pieceElement.textContent = this.getPieceSymbol(piece.type, piece.color);
        pieceElement.style.color = piece.color === 'white' ? '#f0d9b5' : '#3d2817';
        pieceElement.style.textShadow = piece.color === 'white' 
            ? '1px 1px 2px rgba(0,0,0,0.3)' 
            : '1px 1px 2px rgba(255,255,255,0.3)';

        square.innerHTML = '';
        square.appendChild(pieceElement);
        square.setAttribute('aria-label', `Casa ${pos}, ${piece.color === 'white' ? 'brancas' : 'pretas'}: ${this.getPieceName(piece.type)}`);
    }

    getPieceSymbol(type, color) {
        const baseSymbol = this.pieceSymbols[type];
        if (!baseSymbol) return '';
        
        return baseSymbol;
    }

    clearPieces() {
        this.squares.forEach(square => {
            square.innerHTML = '';
            square.setAttribute('aria-label', `Casa ${square.dataset.pos}, vazia`);
        });
    }

    getPieceName(type) {
        return ({p: 'peão', r: 'torre', n: 'cavalo', b: 'bispo', q: 'dama', k: 'rei'})[type] || 'peça';
    }

    handleKeydown(event, pos) {
        const { row, col } = this.posToRowCol(pos);
        const directions = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
        if (directions[event.key]) {
            event.preventDefault();
            const [rowDelta, colDelta] = directions[event.key];
            const nextRow = Math.max(0, Math.min(7, row + rowDelta));
            const nextCol = Math.max(0, Math.min(7, col + colDelta));
            const next = this.rowColToPos(nextRow, nextCol);
            this.focusSquare(next, true);
            return;
        }
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            this.onSquareClickCallback?.(pos);
        }
    }

    focusSquare(pos, moveFocus = true) {
        this.focusedSquare = pos;
        this.squares.forEach((square) => { square.tabIndex = square.dataset.pos === pos ? 0 : -1; });
        if (moveFocus) this.squares.get(pos)?.focus({ preventScroll: true });
    }

    selectSquare(pos) {
        this.deselectSquare();
        const square = this.squares.get(pos);
        if (square) {
            square.classList.add('selected');
            this.selectedSquare = pos;
        }
    }

    deselectSquare() {
        if (this.selectedSquare) {
            const square = this.squares.get(this.selectedSquare);
            if (square) {
                square.classList.remove('selected');
            }
            this.selectedSquare = null;
        }
    }

    highlightSquares(positions) {
        this.clearHighlights();
        positions.forEach(pos => {
            const square = this.squares.get(pos);
            if (square) {
                square.classList.add('highlight');
                this.highlightedSquares.add(pos);
            }
        });
    }

    clearHighlights() {
        this.highlightedSquares.forEach(pos => {
            const square = this.squares.get(pos);
            if (square) {
                square.classList.remove('highlight');
            }
        });
        this.highlightedSquares.clear();
    }

    getSelectedSquare() {
        return this.selectedSquare;
    }

    onSquareClick(callback) {
        this.onSquareClickCallback = callback;
    }

    setOnSquareClick(callback) {
        this.onSquareClickCallback = callback;
    }
}
