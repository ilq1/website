/**
 * Скрипт для автоматического изменения высоты textarea.
 * Упрощенная версия для восстановления функционала.
 */
(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
  typeof define === 'function' && define.amd ? define(factory) :
  (global.autosize = factory());
}(this, (function () { 'use strict';

  function autosize(el) {
    if (!el || el.nodeName !== 'TEXTAREA') return;

    function setHeight() {
      el.style.height = 'auto';
      el.style.height = el.scrollHeight + 'px';
    }

    el.addEventListener('input', setHeight);
    setHeight();
    
    // Возвращаем функцию для ручного обновления, если нужно
    return setHeight;
  }

  return autosize;
})));