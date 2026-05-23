import { mountIsland } from '../shared/mount-island';
import { SignupForm } from './SignupForm';

mountIsland('auth-root', <SignupForm requireInviteCode />);
