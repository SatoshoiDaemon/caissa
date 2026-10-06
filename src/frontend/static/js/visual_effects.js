class CaissaMotion {
    constructor() {
        this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        this.pointerFine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
        this.frame = null;
        this.pointerTarget = null;
        this.pendingPointer = null;
        this.ambient = { x: 50, y: 12, strength: 0 };
        this.ambientTarget = { x: 50, y: 12, strength: 0 };
        this.surfaceScale = 0.68;
        this.observer = null;
    }

    initialize() {
        this.observeViewTransitions();
        this.observeMechanicalDisplays();
        this.observeInteractiveSurfaces();
        this.observeDialogs();
        this.observeToasts();
        this.observeRoomList();
        this.observeArenaState();
        this.observeBackgroundSurface();
        this.bindPressFeedback();

        if (this.pointerFine && !this.reduceMotion) {
            this.bindAmbientPointer();
        }
    }

    observeInteractiveSurfaces() {
        const register = (root = document) => {
            root.querySelectorAll?.('.play-tile, .room-card, .board-frame').forEach((element) => {
                if (element.dataset.motionReady) return;
                element.dataset.motionReady = 'true';
                this.bindTilt(element);
            });
        };

        register();
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) register(node);
            }));
        });
        this.observer.observe(document.body, { childList: true, subtree: true });
    }

    bindTilt(element) {
        if (!this.pointerFine || this.reduceMotion) return;
        element.addEventListener('pointermove', (event) => {
            const bounds = element.getBoundingClientRect();
            const x = (event.clientX - bounds.left) / bounds.width - 0.5;
            const y = (event.clientY - bounds.top) / bounds.height - 0.5;
            element.style.setProperty('--tilt-x', `${(x * 2.4).toFixed(2)}deg`);
            element.style.setProperty('--tilt-y', `${(-y * 2.4).toFixed(2)}deg`);
            element.style.setProperty('--surface-x', `${((x + 0.5) * 100).toFixed(1)}%`);
            element.style.setProperty('--surface-y', `${((y + 0.5) * 100).toFixed(1)}%`);
        }, { passive: true });
        element.addEventListener('pointerleave', () => {
            element.style.setProperty('--tilt-x', '0deg');
            element.style.setProperty('--tilt-y', '0deg');
            element.style.setProperty('--surface-x', '50%');
            element.style.setProperty('--surface-y', '50%');
        }, { passive: true });
    }

    bindAmbientPointer() {
        const shell = document.querySelector('.app-shell');
        if (!shell) return;
        shell.addEventListener('pointermove', (event) => {
            this.ambientTarget.x = event.clientX / window.innerWidth * 100;
            this.ambientTarget.y = event.clientY / window.innerHeight * 100;
            this.ambientTarget.strength = 1;
            this.startAmbientFrame(shell);
        }, { passive: true });
        shell.addEventListener('pointerleave', () => {
            this.ambientTarget.strength = 0;
            this.startAmbientFrame(shell);
        }, { passive: true });
    }

    startAmbientFrame(shell) {
        if (this.frame) return;
        const tick = () => {
            const ease = 0.14;
            this.ambient.x += (this.ambientTarget.x - this.ambient.x) * ease;
            this.ambient.y += (this.ambientTarget.y - this.ambient.y) * ease;
            this.ambient.strength += (this.ambientTarget.strength - this.ambient.strength) * ease;

            const shadowX = ((50 - this.ambient.x) / 50) * 3;
            const shadowY = ((50 - this.ambient.y) / 50) * 3 + 2;
            const influence = this.ambient.strength * this.surfaceScale;
            shell.style.setProperty('--ambient-x', `${this.ambient.x.toFixed(2)}%`);
            shell.style.setProperty('--ambient-y', `${this.ambient.y.toFixed(2)}%`);
            shell.style.setProperty('--grid-influence-opacity', influence.toFixed(3));
            shell.style.setProperty('--grid-shadow-opacity', (influence * 0.62).toFixed(3));
            shell.style.setProperty('--grid-shadow-x', `${shadowX.toFixed(2)}px`);
            shell.style.setProperty('--grid-shadow-y', `${shadowY.toFixed(2)}px`);

            const settled = Math.abs(this.ambientTarget.x - this.ambient.x) < 0.08
                && Math.abs(this.ambientTarget.y - this.ambient.y) < 0.08
                && Math.abs(this.ambientTarget.strength - this.ambient.strength) < 0.01;
            if (!settled || this.ambientTarget.strength > 0) {
                this.frame = requestAnimationFrame(tick);
            } else {
                this.frame = null;
            }
        };
        this.frame = requestAnimationFrame(tick);
    }

    observeBackgroundSurface() {
        const shell = document.querySelector('.app-shell');
        if (!shell) return;
        const update = () => {
            const visible = (id) => !document.getElementById(id)?.classList.contains('hidden');
            if (visible('game-container')) this.surfaceScale = 0.12;
            else if (visible('profile-page')) this.surfaceScale = 0.42;
            else if (visible('login-page')) this.surfaceScale = 0.92;
            else this.surfaceScale = 0.68;
        };
        update();
        const observer = new MutationObserver(update);
        ['login-page', 'profile-page', 'menu-principal', 'game-container'].forEach((id) => {
            const element = document.getElementById(id);
            if (element) observer.observe(element, { attributes: true, attributeFilter: ['class'] });
        });
    }

    bindPressFeedback() {
        document.addEventListener('pointerdown', (event) => {
            const target = event.target.closest?.('.button, .play-tile, .room-card-actions button, .promotion-option');
            target?.classList.add('is-pressed');
        }, { passive: true });
        ['pointerup', 'pointercancel', 'pointerleave'].forEach((eventName) => {
            document.addEventListener(eventName, (event) => {
                event.target.closest?.('.is-pressed')?.classList.remove('is-pressed');
            }, { passive: true });
        });
    }

    observeMechanicalDisplays() {
        const animate = (element) => {
            if (this.reduceMotion || !element || element.dataset.lastMotionText === element.textContent) return;
            element.dataset.lastMotionText = element.textContent;
            element.classList.remove('mechanical-flip');
            void element.offsetWidth;
            element.classList.add('mechanical-flip');
            window.setTimeout(() => element.classList.remove('mechanical-flip'), 460);
        };
        const displays = document.querySelectorAll('.clock, #move-text, #move-count, #connection-status');
        displays.forEach((element) => {
            element.dataset.lastMotionText = element.textContent;
            new MutationObserver(() => animate(element)).observe(element, { childList: true, characterData: true, subtree: true });
        });
    }

    observeDialogs() {
        document.querySelectorAll('.dialog').forEach((dialog) => {
            let wasHidden = dialog.classList.contains('hidden');
            new MutationObserver(() => {
                const isHidden = dialog.classList.contains('hidden');
                if (isHidden === wasHidden) return;
                wasHidden = isHidden;
                if (isHidden) return;
                dialog.classList.remove('dialog-entering');
                void dialog.offsetWidth;
                dialog.classList.add('dialog-entering');
            }).observe(dialog, { attributes: true, attributeFilter: ['class'] });
        });
    }

    observeToasts() {
        const region = document.getElementById('toast-region');
        if (!region) return;
        new MutationObserver((mutations) => {
            mutations.forEach((mutation) => mutation.addedNodes.forEach((node) => {
                if (node.nodeType !== Node.ELEMENT_NODE) return;
                node.classList.add('toast-entering');
                window.setTimeout(() => node.classList.remove('toast-entering'), 360);
            }));
        }).observe(region, { childList: true });
    }

    observeRoomList() {
        const list = document.getElementById('rooms-list');
        if (!list) return;
        new MutationObserver((mutations) => {
            const cards = [];
            mutations.forEach((mutation) => mutation.addedNodes.forEach((node) => {
                if (node.nodeType !== Node.ELEMENT_NODE) return;
                if (node.classList.contains('room-card')) cards.push(node);
                node.querySelectorAll?.('.room-card').forEach((card) => cards.push(card));
            }));
            cards.forEach((card, index) => {
                card.style.setProperty('--room-delay', `${Math.min(index * 36, 180)}ms`);
                card.classList.add('room-card-entering');
            });
        }).observe(list, { childList: true, subtree: true });
    }

    observeArenaState() {
        const arena = document.getElementById('game-container');
        if (!arena) return;
        const history = document.getElementById('move-history');
        const spectator = document.getElementById('spectator-banner');
        const connection = document.getElementById('connection-status');
        const status = document.getElementById('move-text');

        if (history) new MutationObserver(() => this.pulse(history, 'history-update', 260))
            .observe(history, { childList: true, characterData: true, subtree: true });
        if (spectator) {
            let wasHidden = spectator.classList.contains('hidden');
            new MutationObserver(() => {
                const isHidden = spectator.classList.contains('hidden');
                if (isHidden === wasHidden) return;
                wasHidden = isHidden;
                if (!isHidden) this.pulse(spectator, 'spectator-enter', 420);
            }).observe(spectator, { attributes: true, attributeFilter: ['class'] });
        }
        if (connection) new MutationObserver(() => this.pulse(connection, 'connection-change', 360))
            .observe(connection, { attributes: true, attributeFilter: ['data-state'], childList: true, characterData: true, subtree: true });
        if (status) new MutationObserver(() => {
            const value = status.textContent || '';
            const important = /XEQUE|AFOGAMENTO|EMPAT|VENCEU|desconect|encerrad/i.test(value);
            this.pulse(status, important ? 'state-emphasis' : 'state-update', important ? 520 : 260);
        }).observe(status, { childList: true, characterData: true, subtree: true });
    }

    pulse(element, className, duration) {
        if (!element || this.reduceMotion) return;
        element.classList.remove(className);
        void element.offsetWidth;
        element.classList.add(className);
        window.setTimeout(() => element.classList.remove(className), duration);
    }

    observeViewTransitions() {
        ['menu-principal', 'game-container'].forEach((id) => {
            const view = document.getElementById(id);
            if (!view) return;
            let wasHidden = view.classList.contains('hidden');
            new MutationObserver(() => {
                const isHidden = view.classList.contains('hidden');
                if (isHidden === wasHidden || isHidden || this.reduceMotion) {
                    wasHidden = isHidden;
                    return;
                }
                wasHidden = isHidden;
                view.classList.remove('scene-arrive');
                void view.offsetWidth;
                view.classList.add('scene-arrive');
            }).observe(view, { attributes: true, attributeFilter: ['class'] });
        });
    }
}

window.caissaMotion = new CaissaMotion();
window.caissaMotion.initialize();
