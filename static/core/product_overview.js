(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    ready(function () {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        const menuBtn = document.getElementById('mobile-menu-btn');
        const closeBtn = document.getElementById('sidebar-close-btn');

        if (!sidebar || !overlay || !menuBtn) {
            return;
        }

        const MOBILE_BREAKPOINT = 1024;

        function isDrawerMode() {
            return window.innerWidth <= MOBILE_BREAKPOINT;
        }

        function openSidebar() {
            overlay.removeAttribute('hidden');
            sidebar.classList.add('open');
            overlay.classList.add('visible');
            document.body.classList.add('toc-open');
            menuBtn.setAttribute('aria-expanded', 'true');
            menuBtn.setAttribute('aria-label', 'Close table of contents');
        }

        function closeSidebar() {
            sidebar.classList.remove('open');
            overlay.classList.remove('visible');
            document.body.classList.remove('toc-open');
            menuBtn.setAttribute('aria-expanded', 'false');
            menuBtn.setAttribute('aria-label', 'Open table of contents');
            window.setTimeout(function () {
                if (!sidebar.classList.contains('open')) {
                    overlay.setAttribute('hidden', '');
                }
            }, 280);
        }

        function toggleSidebar(event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            if (sidebar.classList.contains('open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        }

        menuBtn.addEventListener('click', toggleSidebar);
        if (closeBtn) {
            closeBtn.addEventListener('click', function (event) {
                event.preventDefault();
                closeSidebar();
            });
        }
        overlay.addEventListener('click', closeSidebar);

        document.querySelectorAll('.sidebar a[href^="#"]').forEach(function (link) {
            link.addEventListener('click', function () {
                if (isDrawerMode()) {
                    closeSidebar();
                }
            });
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeSidebar();
            }
        });

        // Sidebar is always a drawer (iPhone-style); close on wide resize optional
        window.addEventListener('resize', function () {
            if (window.innerWidth > 1400 && sidebar.classList.contains('open')) {
                closeSidebar();
            }
        });

        // Wrap tables for horizontal scroll
        document.querySelectorAll('.chapter-content table').forEach(function (table) {
            if (table.parentElement && table.parentElement.classList.contains('table-wrap')) {
                return;
            }
            const wrap = document.createElement('div');
            wrap.className = 'table-wrap';
            table.parentNode.insertBefore(wrap, table);
            wrap.appendChild(table);
        });

        // Active chapter highlight on scroll
        const chapterLinks = document.querySelectorAll('.toc-chapter > a');
        const chapters = document.querySelectorAll('.chapter');

        function updateActiveLink() {
            let current = '';
            chapters.forEach(function (ch) {
                const rect = ch.getBoundingClientRect();
                if (rect.top <= 120) {
                    current = ch.id;
                }
            });
            chapterLinks.forEach(function (link) {
                link.classList.toggle('active', link.getAttribute('href') === '#' + current);
            });
        }

        window.addEventListener('scroll', updateActiveLink, { passive: true });
        updateActiveLink();

        // Reading progress bar
        const progressBar = document.getElementById('read-progress');
        const backToTop = document.getElementById('back-to-top');

        function updateScrollUI() {
            const scrollTop = window.scrollY || document.documentElement.scrollTop;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = docHeight > 0 ? Math.min(100, (scrollTop / docHeight) * 100) : 0;

            if (progressBar) {
                progressBar.style.width = progress + '%';
            }

            if (backToTop) {
                const show = scrollTop > 480;
                backToTop.classList.toggle('visible', show);
                if (show) {
                    backToTop.removeAttribute('hidden');
                } else {
                    backToTop.setAttribute('hidden', '');
                }
            }
        }

        window.addEventListener('scroll', updateScrollUI, { passive: true });
        updateScrollUI();

        if (backToTop) {
            backToTop.addEventListener('click', function () {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }

        // Mermaid diagrams
        if (window.mermaid) {
            window.mermaid.initialize({
                startOnLoad: true,
                theme: 'neutral',
                securityLevel: 'loose',
                flowchart: { useMaxWidth: true },
            });
        }
    });
})();
