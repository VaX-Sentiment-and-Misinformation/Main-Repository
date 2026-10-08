import type { Metadata } from "next";
import Info from "@/pages/info/info";

export const metadata: Metadata = {
  title: "Disease facts | VaX",
  description: "Facts and vaccination schedules for nine vaccine-preventable diseases, from WHO, CDC and the Australian Department of Health.",
};

export default function Page() {
  return <Info />;
}
