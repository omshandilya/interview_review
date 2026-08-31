/**
 * TTSService — Browser-native Text-to-Speech using the Web Speech API.
 *
 * Design principles:
 *  - Zero external dependencies; works in all modern browsers.
 *  - Singleton pattern: one shared instance via `window.tts`.
 *  - Clean callback hooks so any page can react to speech lifecycle.
 *  - Graceful no-op when the browser does not support speechSynthesis.
 *
 * Future-proofing:
 *  - All callers use `window.tts.speak(text, callbacks)`.
 *  - To swap in a premium TTS provider (e.g. Google Cloud TTS, ElevenLabs),
 *    replace only the internals of this file — no template changes needed.
 */

'use strict';

class TTSService {
    constructor() {
        /** @type {SpeechSynthesisUtterance|null} */
        this._utterance = null;

        /** @type {boolean} Whether the user has muted TTS for this session */
        this._muted = this._loadMutePref();

        /** @type {boolean} True while speech is actively playing */
        this._speaking = false;
    }

    // --- Public API ------------------------------------------------------------

    /**
     * Speak the given text string.
     *
     * @param {string}   text        - The text to be spoken.
     * @param {object}   [callbacks] - Optional lifecycle hooks.
     * @param {Function} [callbacks.onStart] - Called when speech begins.
     * @param {Function} [callbacks.onEnd]   - Called when speech finishes or is cancelled.
     * @param {Function} [callbacks.onError] - Called on any speech error.
     */
    speak(text, callbacks = {}) {
        if (!this.isSupported()) {
            callbacks.onEnd?.();
            return;
        }

        if (!text || typeof text !== 'string' || text.trim() === '') {
            callbacks.onEnd?.();
            return;
        }

        // Cancel anything currently playing before starting new speech
        this.stop();

        if (this._muted) {
            // Skip synthesis but still fire onEnd so callers unblock normally
            callbacks.onEnd?.();
            return;
        }

        this._utterance = new SpeechSynthesisUtterance(text.trim());

        // Voice configuration — tuned for interview-style clarity
        this._utterance.rate   = 0.92;  // Slightly slower than default (1.0)
        this._utterance.pitch  = 1.0;
        this._utterance.volume = 1.0;

        // Lifecycle handlers
        this._utterance.onstart = () => {
            this._speaking = true;
            callbacks.onStart?.();
        };

        this._utterance.onend = () => {
            this._speaking = false;
            this._utterance = null;
            callbacks.onEnd?.();
        };

        this._utterance.onerror = (event) => {
            // 'interrupted' and 'canceled' are not real errors —
            // they fire when stop() is called mid-speech.
            if (event.error === 'interrupted' || event.error === 'canceled') {
                return;
            }
            console.warn('[TTSService] SpeechSynthesis error:', event.error);
            this._speaking = false;
            this._utterance = null;
            callbacks.onError?.(event.error);
            callbacks.onEnd?.();  // always unblock callers, even on error
        };

        window.speechSynthesis.speak(this._utterance);
    }

    /**
     * Immediately stop any ongoing speech.
     */
    stop() {
        if (!this.isSupported()) return;
        window.speechSynthesis.cancel();
        this._speaking  = false;
        this._utterance = null;
    }

    /**
     * Toggle mute on/off. Persists choice in sessionStorage for this session.
     *
     * @returns {boolean} The new muted state.
     */
    toggleMute() {
        this._muted = !this._muted;
        this._saveMutePref(this._muted);

        if (this._muted) {
            this.stop();
        }

        return this._muted;
    }

    /** @returns {boolean} True if TTS is currently muted. */
    get isMuted()    { return this._muted; }

    /** @returns {boolean} True if speech is actively playing. */
    get isSpeaking() { return this._speaking; }

    /**
     * @returns {boolean} True if the current browser supports the Web Speech API.
     */
    isSupported() {
        return typeof window !== 'undefined' && 'speechSynthesis' in window;
    }

    // --- Private helpers -------------------------------------------------------

    _loadMutePref() {
        try {
            return sessionStorage.getItem('tts_muted') === 'true';
        } catch {
            return false;  // Private/incognito mode may block sessionStorage
        }
    }

    _saveMutePref(value) {
        try {
            sessionStorage.setItem('tts_muted', String(value));
        } catch {
            // Silently ignore storage errors
        }
    }
}

// --- Singleton -----------------------------------------------------------------
// Expose as window.tts so every template and script can call window.tts.speak()
window.tts = new TTSService();
