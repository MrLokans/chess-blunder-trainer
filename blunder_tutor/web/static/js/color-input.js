window.setupColorInput = function setupColorInput(colorInputEl, hexInputEl, onChange) {
  colorInputEl.addEventListener('input', () => {
    hexInputEl.value = colorInputEl.value.toUpperCase();
    if (onChange) onChange(colorInputEl.value);
  });

  hexInputEl.addEventListener('input', () => {
    const val = hexInputEl.value;
    if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
      colorInputEl.value = val;
      if (onChange) onChange(val);
    }
  });

  hexInputEl.addEventListener('blur', () => {
    let val = hexInputEl.value.trim();
    if (!val.startsWith('#')) val = '#' + val;
    if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
      hexInputEl.value = val.toUpperCase();
      colorInputEl.value = val;
    } else {
      hexInputEl.value = colorInputEl.value.toUpperCase();
    }
  });
};
