const ACTIVE_DROPDOWN = { current: null };

function createDropdown(selectEl) {
  const wrapper = document.createElement('div');
  wrapper.className = 'custom-dropdown';

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'custom-dropdown__trigger';
  trigger.setAttribute('aria-haspopup', 'listbox');
  trigger.setAttribute('aria-expanded', 'false');

  const label = document.createElement('span');
  label.className = 'custom-dropdown__label';

  const arrow = document.createElement('span');
  arrow.className = 'custom-dropdown__arrow';
  arrow.innerHTML = `<svg width="12" height="8" viewBox="0 0 12 8" fill="none"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  trigger.appendChild(label);
  trigger.appendChild(arrow);

  const listbox = document.createElement('ul');
  listbox.className = 'custom-dropdown__options';
  listbox.setAttribute('role', 'listbox');

  function buildOptions() {
    listbox.innerHTML = '';
    for (const opt of selectEl.options) {
      const li = document.createElement('li');
      li.className = 'custom-dropdown__option';
      li.setAttribute('role', 'option');
      li.dataset.value = opt.value;
      li.textContent = opt.textContent;
      if (opt.selected) li.classList.add('custom-dropdown__option--selected');
      li.addEventListener('click', () => selectOption(li, opt.value));
      listbox.appendChild(li);
    }
  }

  function selectOption(li, value) {
    selectEl.value = value;
    selectEl.dispatchEvent(new Event('change', { bubbles: true }));
    syncLabel();
    listbox.querySelectorAll('.custom-dropdown__option--selected')
      .forEach(el => el.classList.remove('custom-dropdown__option--selected'));
    li.classList.add('custom-dropdown__option--selected');
    close();
  }

  function syncLabel() {
    const selected = selectEl.options[selectEl.selectedIndex];
    label.textContent = selected ? selected.textContent : '';
  }

  function open() {
    if (ACTIVE_DROPDOWN.current && ACTIVE_DROPDOWN.current !== wrapper) {
      ACTIVE_DROPDOWN.current.querySelector('.custom-dropdown__trigger')
        ?.setAttribute('aria-expanded', 'false');
      ACTIVE_DROPDOWN.current.querySelector('.custom-dropdown__options')
        ?.classList.remove('custom-dropdown__options--open');
    }
    ACTIVE_DROPDOWN.current = wrapper;
    trigger.setAttribute('aria-expanded', 'true');
    listbox.classList.add('custom-dropdown__options--open');
  }

  function close() {
    trigger.setAttribute('aria-expanded', 'false');
    listbox.classList.remove('custom-dropdown__options--open');
    if (ACTIVE_DROPDOWN.current === wrapper) ACTIVE_DROPDOWN.current = null;
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = trigger.getAttribute('aria-expanded') === 'true';
    isOpen ? close() : open();
  });

  trigger.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });

  selectEl.classList.add('hidden');
  selectEl.parentNode.insertBefore(wrapper, selectEl);
  wrapper.appendChild(trigger);
  wrapper.appendChild(listbox);
  wrapper.appendChild(selectEl);

  buildOptions();
  syncLabel();

  const observer = new MutationObserver(() => { buildOptions(); syncLabel(); });
  observer.observe(selectEl, { childList: true, subtree: true, attributes: true });

  return { refresh: () => { buildOptions(); syncLabel(); } };
}

function initDropdowns(root = document) {
  root.querySelectorAll('select:not([data-dropdown-init])').forEach(sel => {
    sel.dataset.dropdownInit = '';
    createDropdown(sel);
  });
}

document.addEventListener('click', () => {
  if (ACTIVE_DROPDOWN.current) {
    ACTIVE_DROPDOWN.current.querySelector('.custom-dropdown__trigger')
      ?.setAttribute('aria-expanded', 'false');
    ACTIVE_DROPDOWN.current.querySelector('.custom-dropdown__options')
      ?.classList.remove('custom-dropdown__options--open');
    ACTIVE_DROPDOWN.current = null;
  }
});

export { createDropdown, initDropdowns };
