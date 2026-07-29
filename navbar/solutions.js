(function () {
  var tabs = document.querySelectorAll('.tab');
  var panels = {
    seekers: document.getElementById('panel-seekers'),
    campus: document.getElementById('panel-campus'),
    hr: document.getElementById('panel-hr'),
    enterprise: document.getElementById('panel-enterprise')
  };

  function activateTab(targetId) {
    tabs.forEach(function (tab) {
      var isActive = tab.getAttribute('data-target') === targetId;
      tab.classList.toggle('is-active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    Object.keys(panels).forEach(function (key) {
      var panel = panels[key];
      if (!panel) return;
      if (key === targetId) {
        panel.classList.add('is-active');
        panel.removeAttribute('hidden');
      } else {
        panel.classList.remove('is-active');
        panel.setAttribute('hidden', '');
      }
    });
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.getAttribute('data-target');
      if (target) activateTab(target);
    });
  });

  var activeTab = document.querySelector('.tab.is-active');
  if (activeTab) {
    var initialTarget = activeTab.getAttribute('data-target');
    if (initialTarget) activateTab(initialTarget);
  }
})();
