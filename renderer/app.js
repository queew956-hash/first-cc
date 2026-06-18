// ===== Timer Configuration =====
const CONFIG = {
  work: 25 * 60,        // 25 minutes
  shortBreak: 5 * 60,   // 5 minutes
  longBreak: 15 * 60,   // 15 minutes
  longBreakInterval: 4, // Long break after 4 pomodoros
};

// ===== State =====
const STATE = {
  mode: 'work',         // 'work' | 'short-break' | 'long-break'
  timerState: 'idle',   // 'idle' | 'running' | 'paused'
  remaining: CONFIG.work,
  totalDuration: CONFIG.work,
  completedPomodoros: 0,
  intervalId: null,
};

// ===== DOM Elements =====
const timeDisplay = document.getElementById('time-display');
const modeLabel = document.getElementById('mode-label');
const progressRing = document.getElementById('progress-ring');
const btnStart = document.getElementById('btn-start');
const btnPause = document.getElementById('btn-pause');
const btnReset = document.getElementById('btn-reset');
const btnSkip = document.getElementById('btn-skip');
const tomatoIcons = document.getElementById('tomato-icons');
const countLabel = document.getElementById('count-label');
const toggleOnTop = document.getElementById('toggle-ontop');
const body = document.body;

// ===== Ring Circumference =====
const RING_RADIUS = 88;
const CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS; // ~552.92
progressRing.style.strokeDasharray = `${CIRCUMFERENCE}`;
progressRing.style.strokeDashoffset = '0';

// ===== Sound =====
let audioCtx = null;

function playNotificationSound() {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }

    // Play a pleasant three-tone chime
    const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
    const duration = 0.15;

    notes.forEach((freq, i) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.25, audioCtx.currentTime + i * duration);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + i * duration + 0.3);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(audioCtx.currentTime + i * duration);
      osc.stop(audioCtx.currentTime + i * duration + 0.3);
    });
  } catch (e) {
    // Audio not available — silently ignore
  }
}

// ===== Helpers =====
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function getModeLabel(mode) {
  switch (mode) {
    case 'work': return '🔴 专注时间';
    case 'short-break': return '🟢 短休息';
    case 'long-break': return '🔵 长休息';
    default: return '';
  }
}

function setBodyMode(mode) {
  body.classList.remove('mode-work', 'mode-short-break', 'mode-long-break');
  body.classList.add(`mode-${mode}`);
}

function updateRingProgress(fraction) {
  const offset = CIRCUMFERENCE * (1 - fraction);
  progressRing.style.strokeDashoffset = offset.toString();
}

function updateDisplay() {
  timeDisplay.textContent = formatTime(STATE.remaining);
  modeLabel.textContent = getModeLabel(STATE.mode);
  const fraction = STATE.totalDuration > 0
    ? STATE.remaining / STATE.totalDuration
    : 0;
  updateRingProgress(fraction);
}

function updateTomatoCounter() {
  const count = STATE.completedPomodoros;
  if (count === 0) {
    tomatoIcons.textContent = '';
    countLabel.textContent = '0 个番茄';
    return;
  }

  // Show up to 8 tomato emojis, then use a number
  const displayCount = Math.min(count, 8);
  tomatoIcons.textContent = '🍅'.repeat(displayCount);
  countLabel.textContent = `${count} 个番茄`;
}

function updateButtons() {
  switch (STATE.timerState) {
    case 'idle':
      btnStart.disabled = false;
      btnPause.disabled = true;
      btnReset.disabled = true;
      btnSkip.disabled = false;
      break;
    case 'running':
      btnStart.disabled = true;
      btnPause.disabled = false;
      btnReset.disabled = false;
      btnSkip.disabled = false;
      break;
    case 'paused':
      btnStart.disabled = false;
      btnPause.disabled = true;
      btnReset.disabled = false;
      btnSkip.disabled = false;
      break;
  }
}

// ===== Timer Logic =====
function clearTimer() {
  if (STATE.intervalId) {
    clearInterval(STATE.intervalId);
    STATE.intervalId = null;
  }
}

function startTimer() {
  if (STATE.timerState === 'running') return;

  STATE.timerState = 'running';
  updateButtons();

  STATE.intervalId = setInterval(() => {
    STATE.remaining--;

    if (STATE.remaining <= 0) {
      STATE.remaining = 0;
      updateDisplay();
      timerComplete();
      return;
    }

    updateDisplay();
  }, 1000);

  updateDisplay();
}

function pauseTimer() {
  if (STATE.timerState !== 'running') return;

  STATE.timerState = 'paused';
  clearTimer();
  updateButtons();
}

function resetTimer() {
  clearTimer();
  STATE.timerState = 'idle';
  STATE.remaining = STATE.totalDuration;
  updateDisplay();
  updateButtons();
}

function skipToNext() {
  clearTimer();
  // Mark current session as complete
  timerComplete(true);
}

async function timerComplete(skipped = false) {
  clearTimer();

  // If work was completed, increment pomodoro count
  if (STATE.mode === 'work' && !skipped) {
    STATE.completedPomodoros++;
    updateTomatoCounter();

    // Send notification
    try {
      await window.pomodoroAPI.sendNotification(
        '🍅 番茄钟完成！',
        `已完成 ${STATE.completedPomodoros} 个番茄，休息一下吧~`
      );
    } catch (e) {
      // Notification might not be available
    }
  } else if (STATE.mode !== 'work') {
    // Break is over — notify
    try {
      await window.pomodoroAPI.sendNotification(
        '⏰ 休息结束',
        '准备开始新的番茄钟吧！'
      );
    } catch (e) {
      // ignore
    }
  }

  playNotificationSound();

  // Transition to next mode
  if (STATE.mode === 'work') {
    // After work, determine which break
    if (STATE.completedPomodoros % CONFIG.longBreakInterval === 0) {
      STATE.mode = 'long-break';
      STATE.totalDuration = CONFIG.longBreak;
    } else {
      STATE.mode = 'short-break';
      STATE.totalDuration = CONFIG.shortBreak;
    }
  } else {
    // After break, go back to work
    STATE.mode = 'work';
    STATE.totalDuration = CONFIG.work;
  }

  STATE.timerState = 'idle';
  STATE.remaining = STATE.totalDuration;
  setBodyMode(STATE.mode);
  updateDisplay();
  updateButtons();
}

// ===== Event Listeners =====
btnStart.addEventListener('click', startTimer);
btnPause.addEventListener('click', pauseTimer);
btnReset.addEventListener('click', resetTimer);
btnSkip.addEventListener('click', skipToNext);

// Always on top toggle
toggleOnTop.addEventListener('change', async () => {
  try {
    const isOnTop = await window.pomodoroAPI.toggleAlwaysOnTop();
    toggleOnTop.checked = isOnTop;
  } catch (e) {
    // ignore
  }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  // Ignore if user is typing in an input
  if (e.target.tagName === 'INPUT') return;

  switch (e.code) {
    case 'Space':
      e.preventDefault();
      if (STATE.timerState === 'running') {
        pauseTimer();
      } else {
        startTimer();
      }
      break;
    case 'KeyR':
      if (e.metaKey || e.ctrlKey) break; // Don't intercept browser refresh
      resetTimer();
      break;
    case 'KeyS':
      if (e.metaKey || e.ctrlKey) break;
      skipToNext();
      break;
  }
});

// ===== Initial Render =====
setBodyMode(STATE.mode);
updateDisplay();
updateTomatoCounter();
updateButtons();
