import { useState, useEffect, useRef, useCallback } from 'preact/hooks';

interface VimInputProps {
  visible: boolean;
  game: ChessInstance | null;
  interactive: boolean;
  onMove: (move: { san: string; from: string; to: string; promotion?: string }) => void;
  onClose: () => void;
}

export function VimInput({ visible, game, interactive, onMove, onClose }: VimInputProps): preact.JSX.Element | null {
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [shaking, setShaking] = useState(false);
  const fieldRef = useRef<HTMLInputElement>(null);

  const updateSuggestions = useCallback((text: string) => {
    if (!game) {
      setSuggestions([]);
      setSelectedIndex(-1);
      return;
    }
    const moves = game.moves();
    const filtered = text
      ? moves.filter(m => m.toLowerCase().startsWith(text.toLowerCase()))
      : moves;
    setSuggestions(filtered);
    setSelectedIndex(-1);
  }, [game]);

  useEffect(() => {
    if (visible && fieldRef.current) {
      setValue('');
      setError('');
      setSelectedIndex(-1);
      fieldRef.current.focus();
      updateSuggestions('');
    }
  }, [visible, updateSuggestions]);

  const tryMove = useCallback((moveStr: string) => {
    if (!game || !interactive) return;
    const legalMoves = game.moves({ verbose: true });
    const isPromotion = legalMoves.some(
      m => m.san === moveStr && m.flags.includes('p'),
    );
    const result = game.move(moveStr);
    if (result) {
      onMove({
        san: result.san,
        from: result.from,
        to: result.to,
        promotion: isPromotion ? 'q' : result.promotion,
      });
      onClose();
    } else {
      setError(t('trainer.vim.illegal_move'));
      setShaking(true);
    }
  }, [game, interactive, onMove, onClose]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
      return;
    }

    if (e.key === 'Enter') {
      e.preventDefault();
      const moveStr = selectedIndex >= 0 && suggestions[selectedIndex]
        ? suggestions[selectedIndex]
        : value;
      if (moveStr) tryMove(moveStr);
      return;
    }

    if (e.key === 'Tab') {
      e.preventDefault();
      if (suggestions.length === 0) return;
      if (e.shiftKey) {
        setSelectedIndex(i => i <= 0 ? suggestions.length - 1 : i - 1);
      } else {
        setSelectedIndex(i => (i + 1) % suggestions.length);
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, suggestions.length - 1));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
      return;
    }
  }, [suggestions, selectedIndex, value, tryMove, onClose]);

  const handleInput = useCallback((e: Event) => {
    const text = (e.currentTarget as HTMLInputElement).value;
    setValue(text);
    setError('');
    setShaking(false);
    updateSuggestions(text);
  }, [updateSuggestions]);

  const handleAnimationEnd = useCallback(() => {
    setShaking(false);
  }, []);

  if (!visible) return null;

  const maxVisible = 8;
  const visibleSuggestions = suggestions.slice(0, maxVisible);
  const hasMore = suggestions.length > maxVisible;
  const showSuggestions = suggestions.length > 0
    && !(suggestions.length === 1 && suggestions[0] === value.trim());

  return (
    <div class={`vim-input-overlay active ${shaking ? 'shake' : ''}`} id="vimInput" onAnimationEnd={handleAnimationEnd}>
      <span class="vim-input-prefix">:</span>
      <input
        ref={fieldRef}
        type="text"
        class="vim-input-field"
        id="vimInputField"
        value={value}
        onInput={handleInput}
        onKeyDown={handleKeyDown}
        autocomplete="off"
        spellcheck={false}
        placeholder={t('trainer.vim.placeholder')}
      />
      {error && <div class="vim-input-error visible" id="vimInputError">{error}</div>}
      <div class={`vim-suggestions ${showSuggestions ? 'visible' : ''}`} id="vimSuggestions">
        {visibleSuggestions.map((s, i) => {
          const matchLen = value.trim().length;
          return (
            <span
              key={s}
              class={`vim-suggestion ${i === selectedIndex ? 'selected' : ''}`}
              onMouseDown={(e) => { e.preventDefault(); tryMove(s); }}
            >
              {matchLen > 0 ? <b>{s.slice(0, matchLen)}</b> : null}{s.slice(matchLen)}
            </span>
          );
        })}
        {hasMore && (
          <span class="vim-suggestion more">+{suggestions.length - maxVisible}</span>
        )}
      </div>
    </div>
  );
}
