/**
 * TTSService � Browser-native Text-to-Speech using the Web Speech API.
 *
 * Design principles:
 *  - Google Cloud Neural2 is the primary narrator.
 *  - Browser-native speech is an automatic fallback.
 *  - Singleton pattern: one shared instance via `window.tts`.
 *  - Clean callback hooks so any page can react to speech lifecycle.
 *  - Graceful no-op when the browser does not support speechSynthesis.
 *
 * Future-proofing:
 *  - All callers use `window.tts.speak(text, callbacks)`.
 *  - To swap in a premium TTS provider (e.g. Google Cloud TTS, ElevenLabs),
 *    replace only the internals of this file � no template changes needed.
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

        /** @type {HTMLAudioElement|null} Cloud TTS audio currently playing */
        this._audio = null;

        /** @type {AbortController|null} In-flight Cloud TTS request */
        this._requestController = null;
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

        const normalizedText = text.trim();
        this._speakWithCloud(normalizedText, callbacks).catch((error) => {
            // A credential, quota, or network error must never block an interview.
            if (error?.name !== 'AbortError') {
                console.info('[TTSService] Cloud TTS unavailable; using browser voice.', error);
                this._speakWithBrowser(normalizedText, callbacks);
            }
        });
        return;

        /* Legacy browser-only implementation retained below for reference.
        this._utterance = new SpeechSynthesisUtterance(text.trim());

        // Voice configuration � tuned for interview-style clarity
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
            // 'interrupted' and 'canceled' are not real errors �
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
        */
    }

    async _speakWithCloud(text, callbacks) {
        this._requestController = new AbortController();
        const response = await fetch('/tts/synthesize/', {
            method: 'POST',
            credentials: 'same-origin',
            signal: this._requestController.signal,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this._csrfToken(),
            },
            body: JSON.stringify({ text }),
        });

        if (!response.ok) {
            throw new Error(`Cloud TTS returned ${response.status}`);
        }

        const audioUrl = URL.createObjectURL(await response.blob());
        const audio = new Audio(audioUrl);
        this._audio = audio;
        this._requestController = null;

        audio.onplay = () => {
            this._speaking = true;
            callbacks.onStart?.();
        };
        audio.onended = () => this._finishAudio(audioUrl, callbacks);
        audio.onerror = () => {
            if (this._audio !== audio) return;
            this._discardAudio(audioUrl);
            this._speakWithBrowser(text, callbacks);
        };

        try {
            await audio.play();
        } catch (error) {
            if (this._audio === audio) {
                this._discardAudio(audioUrl);
                throw error;
            }
        }
    }

    _speakWithBrowser(text, callbacks) {
        if (!this.isBrowserSupported()) {
            callbacks.onError?.('No text-to-speech provider is available.');
            callbacks.onEnd?.();
            return;
        }

        this._utterance = new SpeechSynthesisUtterance(text);
        this._utterance.rate = 0.92;
        this._utterance.pitch = 1.0;
        this._utterance.volume = 1.0;
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
            if (event.error === 'interrupted' || event.error === 'canceled') return;
            console.warn('[TTSService] Browser TTS error:', event.error);
            this._speaking = false;
            this._utterance = null;
            callbacks.onError?.(event.error);
            callbacks.onEnd?.();
        };
        window.speechSynthesis.speak(this._utterance);
    }

    _finishAudio(audioUrl, callbacks) {
        this._discardAudio(audioUrl);
        this._speaking = false;
        callbacks.onEnd?.();
    }

    _discardAudio(audioUrl) {
        this._audio = null;
        URL.revokeObjectURL(audioUrl);
    }

    _csrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    /**
     * Immediately stop any ongoing speech.
     */
    stop() {
        this._requestController?.abort();
        this._requestController = null;
        if (this._audio) {
            this._audio.onended = null;
            this._audio.onerror = null;
            this._audio.pause();
            this._audio = null;
        }
        if (this.isBrowserSupported()) window.speechSynthesis.cancel();
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
        return typeof window !== 'undefined' &&
            (typeof Audio !== 'undefined' || this.isBrowserSupported());
    }

    isBrowserSupported() {
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
