export type ProfilePlatform = 'lichess' | 'chesscom';

export const PLATFORM_LABEL: Record<ProfilePlatform, string> = {
  lichess: 'Lichess',
  chesscom: 'Chess.com',
};

export interface ProfilePreferences {
  auto_sync_enabled: boolean;
  sync_max_games: number | null;
}

export interface ProfileStatSnapshot {
  mode: string;
  rating: number | null;
  games_count: number;
  synced_at: string | null;
}

export interface Profile {
  id: number;
  platform: ProfilePlatform;
  username: string;
  is_primary: boolean;
  created_at: string;
  last_validated_at: string | null;
  preferences: ProfilePreferences;
  stats: ProfileStatSnapshot[];
  last_game_sync_at: string | null;
  last_stats_sync_at: string | null;
}

export interface ProfilesListResponse {
  profiles: Profile[];
}

export interface ProfileValidateRequest {
  platform: ProfilePlatform;
  username: string;
}

export interface ProfileValidateResponse {
  exists: boolean;
  already_tracked: boolean;
  profile_id: number | null;
  rate_limited: boolean;
}

export interface ProfileCreateRequest {
  platform: ProfilePlatform;
  username: string;
  make_primary?: boolean;
}

export interface ProfilePreferencesPatch {
  auto_sync_enabled?: boolean;
  sync_max_games?: number | null;
}

export interface ProfileUpdateRequest {
  username?: string;
  is_primary?: boolean;
  preferences?: ProfilePreferencesPatch;
}

export interface ProfileSyncDispatchResponse {
  job_id: string;
}

export interface ProfileStatsRefreshResponse {
  stats: ProfileStatSnapshot[];
  last_validated_at: string | null;
}
