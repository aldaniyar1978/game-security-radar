(function() {
    'use strict';

    const loadPreferences = () => {
        const theme = localStorage.getItem('theme') || 'dark';
        const fontSize = localStorage.getItem('fontSize') || 'normal';
        const contrast = localStorage.getItem('contrast') || 'normal';

        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-font-size', fontSize);
        document.documentElement.setAttribute('data-contrast', contrast);
    };

    const setPreference = (key, value) => {
        localStorage.setItem(key, value);
        loadPreferences();
    };

    const createPanel = () => {
        if (document.getElementById('accessibility-panel')) return;

        const panel = document.createElement('div');
        panel.id = 'accessibility-panel';
        panel.innerHTML = `
            <button id="a11y-toggle" title="Accessibility Settings">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
            </button>
            <div id="a11y-menu" class="hidden">
                <h3 style="margin-bottom:1rem; font-size:1.1rem">Настройки доступности</h3>
                
                <div class="a11y-section">
                    <h4>Тема</h4>
                    <div class="btn-group">
                        <button onclick="window.setTheme('light')">🌞 Светлая</button>
                        <button onclick="window.setTheme('dark')">🌙 Темная</button>
                    </div>
                </div>

                <div class="a11y-section">
                    <h4>Размер шрифта</h4>
                    <div class="btn-group">
                        <button onclick="window.setFontSize('small')">A</button>
                        <button onclick="window.setFontSize('normal')">A+</button>
                        <button onclick="window.setFontSize('large')">A++</button>
                    </div>
                </div>

                <div class="a11y-section">
                    <h4>Контраст</h4>
                    <div class="btn-group">
                        <button onclick="window.setContrast('normal')">Обычный</button>
                        <button onclick="window.setContrast('high')">Высокий</button>
                    </div>
                </div>

                <button onclick="window.resetA11y()" style="width:100%; margin-top:0.5rem; padding:0.5rem; background:transparent; border:1px solid var(--border); color:var(--text-muted); cursor:pointer">Сбросить</button>
            </div>
        `;
        document.body.appendChild(panel);

        document.getElementById('a11y-toggle').addEventListener('click', () => {
            document.getElementById('a11y-menu').classList.toggle('hidden');
        });
    };

    window.setTheme = (t) => setPreference('theme', t);
    window.setFontSize = (s) => setPreference('fontSize', s);
    window.setContrast = (c) => setPreference('contrast', c);
    window.resetA11y = () => {
        localStorage.clear();
        loadPreferences();
    };

    document.addEventListener('DOMContentLoaded', () => {
        loadPreferences();
        createPanel();
    });
})();
