import { hasFeature } from '../shared/features';

export function useFeature(name: string): boolean {
  return hasFeature(name);
}
