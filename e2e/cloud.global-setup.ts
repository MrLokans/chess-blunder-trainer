import { captureInvite } from './invite-setup';

export default function globalSetup(): void {
  captureInvite('.tmp-cloud');
}
