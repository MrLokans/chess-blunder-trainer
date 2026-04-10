import { useState, useEffect } from 'preact/hooks';
import { client } from '../../shared/api';
import { applyBoardBackground, applyPieceSet } from '../../shared/board-theme';

interface BoardSettings {
  piece_set: string;
  board_light: string;
  board_dark: string;
}

export function useBoardSettings(): BoardSettings | null {
  const [settings, setSettings] = useState<BoardSettings | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      try {
        const data = await client.settings.getBoard() as BoardSettings;
        setSettings(data);
        applyBoardBackground(data.board_light, data.board_dark);
        applyPieceSet(data.piece_set);
      } catch (err) {
        console.error('Failed to load board settings:', err);
      }
    }
    void load();
  }, []);

  return settings;
}
