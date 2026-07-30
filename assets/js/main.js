/* 스피드배관 — 공통 스크립트
   - 모바일 내비
   - 전국 지역 선택기(시·도 → 시·군·구 → 행정구 → 행정동)
   - 시공 갤러리 라이트박스
   - 스크롤 등장 효과
*/
(function () {
  'use strict';

  var TEL = '010-5183-4300';
  var TEL_HREF = 'tel:01051834300';

  /* ------------------------------------------------------------------ 내비 */
  function initNav() {
    var burger = document.querySelector('.burger');
    var panel = document.querySelector('.mobilenav');
    if (!burger || !panel) return;

    // 모바일 메뉴 목록은 헤더 메가메뉴에서 그대로 복제한다(마크업 중복 제거).
    Array.prototype.forEach.call(panel.querySelectorAll('details[data-clone]'), function (d) {
      var src = document.querySelector(d.getAttribute('data-clone'));
      var box = d.querySelector('.mob-links');
      if (!src || !box) return;
      Array.prototype.forEach.call(src.querySelectorAll('a'), function (a) {
        if (a.closest('.menu__foot')) return;
        var c = a.cloneNode(true);
        box.insertBefore(c, box.firstChild);
      });
    });

    burger.addEventListener('click', function () {
      var open = panel.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open ? 'hidden' : '';
    });

    panel.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        panel.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panel.classList.contains('is-open')) {
        burger.click();
        burger.focus();
      }
    });
  }

  /* -------------------------------------------------------- 지역 선택기 */

  // 데이터 노드를 [{name, children|null}] 형태로 정규화한다.
  function childrenOf(node) {
    if (!node) return null;
    if (node.children) return node.children;          // 시·도
    if (node.districts) return node.districts;        // 일반구를 가진 시
    if (node.dongs) {
      return node.dongs.map(function (d) { return { name: d, leaf: true }; });
    }
    return null;
  }

  // 열 제목은 "부모가 어떤 자식을 가지는가"로 결정한다.
  function levelLabel(node) {
    if (node._all) return '시 · 도';
    if (node.children) return '시 · 군 · 구';
    if (node.districts) return '행정구';
    return '읍 · 면 · 동';
  }

  function RegionPicker(root) {
    this.root = root;
    this.scope = root.getAttribute('data-scope') || '';   // 특정 시·도로 한정
    this.colsEl = root.querySelector('.region-cols');
    this.crumbEl = root.querySelector('.region-crumb');
    this.pickedEl = root.querySelector('.region-picked');
    this.pickedTxt = root.querySelector('.region-picked__name');
    this.pickedSub = root.querySelector('.region-picked__sub');
    this.pickedTel = root.querySelector('.region-picked__tel');
    this.pickedPage = root.querySelector('.region-picked__page');
    this.root_ = root.getAttribute('data-root') || '';
    this.searchEl = root.querySelector('.region-search input');
    this.resultsEl = root.querySelector('.region-results');

    var data = (window.SPEEDPIPE_REGIONS || { regions: [] }).regions;
    if (this.scope) {
      var found = data.filter(function (r) {
        return r.slug === this.scope || r.short === this.scope || r.name === this.scope;
      }, this);
      this.rootNode = found.length ? found[0] : { name: '전국', children: [] };
      this.path = [this.rootNode];       // 시·도가 이미 선택된 상태로 시작
    } else {
      this.rootNode = { name: '전국', children: data, _all: true };
      this.path = [this.rootNode];
    }

    this.index = null;
    this.bind();
    this.render();
  }

  RegionPicker.prototype.bind = function () {
    var self = this;

    this.colsEl.addEventListener('click', function (e) {
      var btn = e.target.closest('.region-item');
      if (!btn) return;
      var depth = parseInt(btn.getAttribute('data-depth'), 10);
      var i = parseInt(btn.getAttribute('data-i'), 10);
      self.select(depth, i);
    });

    if (this.crumbEl) {
      this.crumbEl.addEventListener('click', function (e) {
        var btn = e.target.closest('button[data-depth]');
        if (!btn) return;
        self.path = self.path.slice(0, parseInt(btn.getAttribute('data-depth'), 10) + 1);
        self.render();
      });
    }

    if (this.searchEl) {
      var timer = null;
      this.searchEl.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(function () { self.search(self.searchEl.value.trim()); }, 130);
      });
    }

    if (this.resultsEl) {
      this.resultsEl.addEventListener('click', function (e) {
        var btn = e.target.closest('button[data-path]');
        if (!btn) return;
        self.searchEl.value = '';
        self.applyPath(btn.getAttribute('data-path').split('>'));
      });
    }
  };

  // 검색 인덱스: 모든 말단(동/읍/면) + 시군구를 경로와 함께 담는다.
  RegionPicker.prototype.buildIndex = function () {
    var out = [];
    (function walk(node, trail) {
      var kids = childrenOf(node);
      if (!kids) return;
      kids.forEach(function (kid) {
        var t = trail.concat([kid.name]);
        out.push({ name: kid.name, trail: t, leaf: !childrenOf(kid) });
        walk(kid, t);
      });
    })(this.rootNode, this.scope ? [this.rootNode.name] : []);
    this.index = out;
  };

  RegionPicker.prototype.search = function (q) {
    if (!this.resultsEl) return;
    if (!q) {
      this.resultsEl.hidden = true;
      this.colsEl.hidden = false;
      return;
    }
    if (!this.index) this.buildIndex();

    var hits = [];
    for (var i = 0; i < this.index.length && hits.length < 60; i++) {
      if (this.index[i].name.indexOf(q) === 0) hits.push(this.index[i]);
    }
    if (hits.length < 40) {
      for (var j = 0; j < this.index.length && hits.length < 60; j++) {
        var it = this.index[j];
        if (it.name.indexOf(q) > 0 && hits.indexOf(it) < 0) hits.push(it);
      }
    }

    this.colsEl.hidden = true;
    this.resultsEl.hidden = false;
    if (!hits.length) {
      this.resultsEl.innerHTML = '<p class="region-empty">"' + esc(q) + '" 검색 결과가 없습니다. 지역명을 다시 확인해 주세요.</p>';
      return;
    }
    this.resultsEl.innerHTML = hits.map(function (h) {
      var full = h.trail.join(' › ');
      return '<button type="button" data-path="' + esc(h.trail.join('>')) + '">' +
        '<b>' + hl(h.name, q) + '</b><span>' + esc(full) + '</span></button>';
    }).join('');
  };

  RegionPicker.prototype.applyPath = function (names) {
    var path = [this.rootNode];
    var node = this.rootNode;
    var start = this.scope ? 1 : 0;   // 스코프가 있으면 첫 항목은 이미 root
    for (var i = start; i < names.length; i++) {
      var kids = childrenOf(node) || [];
      var next = null;
      for (var k = 0; k < kids.length; k++) {
        if (kids[k].name === names[i]) { next = kids[k]; break; }
      }
      if (!next) break;
      path.push(next);
      node = next;
    }
    this.path = path;
    if (this.resultsEl) this.resultsEl.hidden = true;
    this.colsEl.hidden = false;
    this.render();
    this.root.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  };

  RegionPicker.prototype.select = function (depth, i) {
    var parent = this.path[depth];
    var kids = childrenOf(parent) || [];
    var picked = kids[i];
    if (!picked) return;
    this.path = this.path.slice(0, depth + 1).concat([picked]);
    this.render();

    // 모바일: 새로 열린 열로 이동
    if (window.matchMedia('(max-width: 860px)').matches) {
      var active = this.colsEl.querySelector('.region-col.is-active');
      if (active) active.scrollIntoView({ block: 'nearest' });
    } else {
      this.colsEl.scrollLeft = this.colsEl.scrollWidth;
    }
  };

  RegionPicker.prototype.render = function () {
    var self = this;
    var html = '';

    for (var depth = 0; depth < this.path.length; depth++) {
      var node = this.path[depth];
      var kids = childrenOf(node);
      if (!kids || !kids.length) continue;

      var selectedName = this.path[depth + 1] ? this.path[depth + 1].name : null;
      var isLast = !this.path[depth + 1];
      var grouped = !!node._all;

      // 그룹 제목이 격자 칸을 가로지르지 않도록, 그룹마다 격자를 따로 연다.
      var items = '<div class="region-col__grid">';
      var lastGroup = null;
      kids.forEach(function (kid, i) {
        if (grouped && kid.area && kid.area !== lastGroup) {
          lastGroup = kid.area;
          items += '</div><div class="region-col__group">' + esc(kid.area) +
                   '</div><div class="region-col__grid">';
        }
        var leaf = !childrenOf(kid);
        items += '<button type="button" class="region-item' + (leaf ? ' is-leaf' : '') +
          '" data-depth="' + depth + '" data-i="' + i + '"' +
          (kid.name === selectedName ? ' aria-selected="true"' : '') + '>' +
          '<span>' + esc(grouped && kid.short ? kid.short : kid.name) + '</span>' +
          '<span class="chev" aria-hidden="true">›</span></button>';
      });
      items += '</div>';

      html += '<div class="region-col' + (isLast ? ' is-active' : '') + '" data-depth="' + depth + '">' +
        '<div class="region-col__head"><span>' + esc(levelLabel(node)) + '</span>' +
        '<span class="count">' + kids.length + '</span></div>' +
        '<div class="region-col__body">' + items + '</div></div>';
    }

    this.colsEl.innerHTML = html || '<p class="region-empty">표시할 지역이 없습니다.</p>';
    this.renderCrumb();
    this.renderPicked();
  };

  RegionPicker.prototype.renderCrumb = function () {
    if (!this.crumbEl) return;
    var parts = [];
    for (var i = 0; i < this.path.length; i++) {
      var name = this.path[i].short || this.path[i].name;
      if (i === this.path.length - 1) {
        parts.push('<span class="cur">' + esc(name) + '</span>');
      } else {
        parts.push('<button type="button" data-depth="' + i + '">' + esc(name) + '</button>');
        parts.push('<span class="sep" aria-hidden="true">›</span>');
      }
    }
    this.crumbEl.innerHTML = parts.join('');
  };

  RegionPicker.prototype.renderPicked = function () {
    if (!this.pickedEl) return;
    var last = this.path[this.path.length - 1];
    var isLeaf = this.path.length > 1 && !childrenOf(last);
    if (!isLeaf) { this.pickedEl.hidden = true; return; }

    var names = this.path.slice(1).map(function (n) { return n.name; });
    var full = names.join(' ');
    this.pickedEl.hidden = false;
    if (this.pickedTxt) this.pickedTxt.textContent = full + ' 출동 가능';
    if (this.pickedSub) {
      this.pickedSub.textContent = full + ' 배관공사 · 하수구막힘 · 누수탐지 24시간 접수 중';
    }
    if (this.pickedTel) {
      this.pickedTel.setAttribute('href', TEL_HREF);
      this.pickedTel.setAttribute('aria-label', full + ' 출동 요청 — 전화 ' + TEL);
      this.pickedTel.innerHTML = '<span aria-hidden="true">📞</span> 지금 전화하기 · ' + TEL;
    }
    if (this.pickedPage) {
      var url = this.pageUrl();
      if (url) {
        this.pickedPage.setAttribute('href', url);
        this.pickedPage.textContent = names[names.length - 1] + ' 페이지 보기';
        this.pickedPage.hidden = false;
      } else {
        this.pickedPage.hidden = true;
      }
    }
  };

  // 선택한 지역의 개별 안내 페이지 주소.
  // regions/<시도>/<시군구>/[<행정구>/]<동>.html
  RegionPicker.prototype.pageUrl = function () {
    var i = 0;
    while (i < this.path.length && !this.path[i].slug) i++;
    if (i >= this.path.length) return '';
    var sido = this.path[i].short.replace(/·/g, '');
    var rest = this.path.slice(i + 1).map(function (n) { return n.name; });
    if (!rest.length) return this.root_ + 'regions/' + encodeURIComponent(sido) + '.html';
    var segs = [sido].concat(rest).map(encodeURIComponent);
    return this.root_ + 'regions/' + segs.join('/') + '.html';
  };

  /* -------------------------------------------------------------- 갤러리 */
  function initGallery() {
    var gallery = document.querySelector('[data-gallery]');
    var box = document.querySelector('.lightbox');
    if (!gallery || !box) return;

    var figs = Array.prototype.slice.call(gallery.querySelectorAll('figure'));
    var imgEl = box.querySelector('img');
    var capEl = box.querySelector('.lightbox__cap');
    var cur = 0;

    function show(i) {
      cur = (i + figs.length) % figs.length;
      var src = figs[cur].querySelector('img');
      var cap = figs[cur].querySelector('figcaption');
      imgEl.src = src.getAttribute('data-full') || src.src;
      imgEl.alt = src.alt;
      capEl.textContent = (cap ? cap.textContent : '') + '  (' + (cur + 1) + '/' + figs.length + ')';
    }
    function open(i) { show(i); box.classList.add('is-open'); document.body.style.overflow = 'hidden'; }
    function close() { box.classList.remove('is-open'); document.body.style.overflow = ''; }

    figs.forEach(function (f, i) {
      f.setAttribute('tabindex', '0');
      f.setAttribute('role', 'button');
      f.addEventListener('click', function () { open(i); });
      f.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(i); }
      });
    });

    box.addEventListener('click', function (e) {
      if (e.target.closest('.lightbox__close') || e.target === box) return close();
      if (e.target.closest('.prev')) return show(cur - 1);
      if (e.target.closest('.next')) return show(cur + 1);
    });
    document.addEventListener('keydown', function (e) {
      if (!box.classList.contains('is-open')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') show(cur - 1);
      if (e.key === 'ArrowRight') show(cur + 1);
    });
  }

  /* --------------------------------------------------------- 등장 효과 */
  function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (!items.length || !('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(items, function (el) { el.classList.add('is-in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
    Array.prototype.forEach.call(items, function (el) { io.observe(el); });
  }

  /* ------------------------------------------------------------- 유틸 */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function hl(name, q) {
    var i = name.indexOf(q);
    if (i < 0) return esc(name);
    return esc(name.slice(0, i)) + '<mark>' + esc(name.slice(i, i + q.length)) + '</mark>' + esc(name.slice(i + q.length));
  }

  /* --------------------------------------------------------------- 시작 */
  function boot() {
    initNav();
    initGallery();
    initReveal();
    Array.prototype.forEach.call(document.querySelectorAll('.region-tool'), function (el) {
      try { new RegionPicker(el); } catch (err) { /* 데이터 미로딩 시 조용히 무시 */ }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
