import { GamePage } from "../../../components/game-page";

export default async function RoomPage({ params }: { params: Promise<{code: string}> }) {
  const { code } = await params;
  const id = code.toUpperCase();
  return <GamePage key={id} id={id} />;
}
