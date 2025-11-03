// Audio recording functionality
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
    }

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.onRecordingComplete(audioBlob);
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.updateUI();
        } catch (error) {
            alert('Microphone access denied. Please allow microphone access.');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.updateUI();
            
            // Stop all tracks
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }

    updateUI() {
        const startBtn = document.getElementById('start-recording');
        const stopBtn = document.getElementById('stop-recording');
        const status = document.getElementById('recording-status');

        if (this.isRecording) {
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            status.textContent = '🔴 Recording...';
            status.style.color = 'red';
        } else {
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            status.textContent = '';
        }
    }

    onRecordingComplete(audioBlob) {
        // Submit the audio file
        this.submitAnswer(audioBlob);
    }

    async submitAnswer(audioBlob) {
        const questionId = document.getElementById('question-id').value;
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'answer.wav');
        formData.append('question_id', questionId);

        // Show loading
        document.getElementById('loading-message').style.display = 'block';

        try {
            const response = await fetch('/submit-answer/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.showFeedback(result);
            } else {
                alert('Failed to submit answer. Please try again.');
            }
        } catch (error) {
            alert('Error submitting answer: ' + error.message);
        } finally {
            document.getElementById('loading-message').style.display = 'none';
        }
    }

    showFeedback(result) {
        const feedbackSection = document.getElementById('feedback-section');
        
        // Update scores with color coding
        this.updateScore('accuracy', result.accuracy);
        this.updateScore('clarity-score', result.clarity_score);
        this.updateScore('completeness-score', result.completeness_score);
        this.updateScore('technical-score', result.technical_accuracy_score);
        
        // Update feedback text sections
        document.getElementById('strengths-text').textContent = result.strengths || 'None identified';
        document.getElementById('improvements-text').textContent = result.improvements || 'None suggested';
        document.getElementById('missing-points-text').textContent = result.missing_points || 'None identified';
        document.getElementById('feedback-text').textContent = result.feedback || 'No general feedback available';
        
        feedbackSection.style.display = 'block';
        document.getElementById('next-question').style.display = 'inline-block';
        document.getElementById('recording-controls').style.display = 'none';
    }
    
    updateScore(elementId, score) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = score + '%';
            
            // Color coding based on score
            element.className = 'score-badge ';
            if (score >= 80) element.className += 'score-excellent';
            else if (score >= 60) element.className += 'score-good';
            else if (score >= 40) element.className += 'score-fair';
            else element.className += 'score-poor';
        }
    }
}

// Initialize audio recorder
let audioRecorder;

document.addEventListener('DOMContentLoaded', function() {
    audioRecorder = new AudioRecorder();

    // Recording controls
    const startBtn = document.getElementById('start-recording');
    const stopBtn = document.getElementById('stop-recording');

    if (startBtn) {
        startBtn.addEventListener('click', () => audioRecorder.startRecording());
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', () => audioRecorder.stopRecording());
    }

    // Topic selection
    const topicButtons = document.querySelectorAll('.topic-btn');
    const topicInput = document.getElementById('topic-input');

    topicButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (topicInput) {
                topicInput.value = btn.textContent.trim();
            }
        });
    });

    // Auto-hide alerts
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    }, 5000);
});

// CSRF token helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}