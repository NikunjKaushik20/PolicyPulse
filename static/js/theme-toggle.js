// Theme Toggle Functionality
const THEME_KEY = 'policypulse-theme';

// Get saved theme or default to light
function getTheme() {
  return localStorage.getItem(THEME_KEY) || 'light';
}

// Set theme
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  updateThemeIcon(theme);
}

// Toggle theme
function toggleTheme() {
  const currentTheme = getTheme();
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  setTheme(newTheme);
}

// Update theme icon
function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.textContent = theme === 'light' ? '🌙' : '☀️';
  }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = getTheme();
  setTheme(savedTheme);
  
  // Add click listener to theme toggle button
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }
});

// Export for use in other scripts
window.themeManager = {
  getTheme,
  setTheme,
  toggleTheme
};
