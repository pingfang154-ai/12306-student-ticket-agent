/**
 * 页面动效 — 导航选中项滑块 + 页面方向性切换过渡
 * 依赖：两页 nav 结构均为 <nav class="top-nav"> <div class="nav-links"> <a>…</a> … </div> </nav>
 * 由 index.html / cases.html 在 </body> 前引入。
 */
(function () {
  'use strict';

  var navLinks = document.querySelector('.top-nav .nav-links');
  if (!navLinks) return;
  var links = Array.prototype.slice.call(navLinks.querySelectorAll('a[href]'));
  if (links.length < 2) return;

  // ---- 1) 创建滑块 ----
  var indicator = document.createElement('span');
  indicator.className = 'nav-indicator';
  navLinks.appendChild(indicator);

  // ---- 2) 滑块定位到指定链接 ----
  function placeIndicator(el, animated) {
    if (!el) return;
    var t = el.getBoundingClientRect();
    var c = navLinks.getBoundingClientRect();
    if (!animated) indicator.style.transition = 'none';
    indicator.style.left = (t.left - c.left) + 'px';
    indicator.style.width = t.width + 'px';
    if (!animated) {
      void indicator.offsetWidth; // 强制 reflow，确保 transition:none 生效
      indicator.style.transition = '';
    }
  }

  // 初始：滑块定位到当前 active 项（无动画）
  var activeEl = navLinks.querySelector('a.active') || links[0];
  placeIndicator(activeEl, false);

  // ---- 3) 点击拦截：滑块移动 → 页面滑出 → 跳转 ----
  // 范围：导航链接 + 首页 hero-actions 里的跨页按钮（如「分享案例」）
  var extraNav = Array.prototype.slice.call(document.querySelectorAll('.hero-actions a[href]'));
  var allNavLinks = links.concat(extraNav);

  function bindNavClick(a) {
    a.addEventListener('click', function (e) {
      var href = a.getAttribute('href');
      if (!href || href === '#' || a.target === '_blank') return;
      var toCases = href.indexOf('cases') !== -1; // 首页→案例库：内容向左滑出
      // 若存在导航滑块（当前页为带导航链接的页面），移动滑块并切换 active 视觉
      if (navLinks) {
        placeIndicator(a, true);
        links.forEach(function (x) { x.classList.remove('active'); });
        a.classList.add('active');
      }
      // 从首页「分享案例」按钮跳转 → 标记案例库页自动展开上传表单
      if (a.getAttribute('data-page-nav') === '1') {
        try { sessionStorage.setItem('expand_case_form', '1'); } catch (err) {}
      }
      // 页面整体滑出
      document.body.classList.add(toCases ? 'page-out-left' : 'page-out-right');
      // 记录进入方向：新页从对侧滑入
      try { sessionStorage.setItem('page_dir', toCases ? 'in-right' : 'in-left'); } catch (err) {}
      e.preventDefault();
      setTimeout(function () { window.location.href = href; }, 340);
    });
  }
  allNavLinks.forEach(bindNavClick);

  // ---- 4) 新页加载：按方向滑入 ----
  var dir = null;
  try { dir = sessionStorage.getItem('page_dir'); sessionStorage.removeItem('page_dir'); } catch (err) {}
  if (dir === 'in-right') document.body.classList.add('page-in-right');
  else if (dir === 'in-left') document.body.classList.add('page-in-left');

  // ---- 5) 动画结束后清理页面类 ----
  // 只清理 page-in-*（滑入结束恢复实时毛玻璃、释放 will-change 合成层）；
  // page-out-* 只出现在旧页（跳转后随页面卸载消失），绝不能提前移除，
  // 否则 forwards 填充失效、元素跳回原位闪烁。
  function cleanupPageClasses() {
    document.body.classList.remove('page-in-right', 'page-in-left');
  }
  document.body.addEventListener('animationend', cleanupPageClasses, { once: true });
  // 兜底：滑入动画时长(380ms) + 50ms 后强制清理（防止 animationend 未触发）
  setTimeout(cleanupPageClasses, 430);
})();
