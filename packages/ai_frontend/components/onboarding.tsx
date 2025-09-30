import { CheckCircle2, Sparkles } from "lucide-react";
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./ui/card";

type OnboardingProps = {
  onComplete: () => void;
  isCompleting?: boolean;
  onSkip?: () => void;
};

const checklist = [
  {
    title: "법령과 판례를 한번에 검색",
    description:
      "관련 법령, 해설, 판례를 통합 검색해 답변과 함께 근거를 제공합니다.",
  },
  {
    title: "문서 초안 작성 지원",
    description:
      "계약서나 의견서 초안을 생성하고 필요한 근거 조항을 자동으로 인용합니다.",
  },
  {
    title: "대화 맥락 유지",
    description:
      "이전 질문 흐름을 유지하며 추가 질문이나 자료 업로드에도 대응합니다.",
  },
];

export function Onboarding({ onComplete, isCompleting, onSkip }: OnboardingProps) {
  return (
    <Card className="mx-auto mt-6 w-full max-w-3xl border-primary/30 bg-background/80 backdrop-blur">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-2 text-primary">
          <Sparkles className="h-5 w-5" />
          <span className="font-semibold text-sm uppercase tracking-wide">
            온보딩
          </span>
        </div>
        <CardTitle className="text-2xl">AI 법률 도우미와 함께 시작하세요</CardTitle>
        <CardDescription className="text-base">
          아래 기능을 훑어보고 준비가 되면 대화를 시작하세요. 언제든지 좌측
          메뉴에서 새로운 상담을 열 수 있습니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {checklist.map((item) => (
          <div className="flex items-start gap-3" key={item.title}>
            <CheckCircle2 className="mt-1 h-5 w-5 text-primary" />
            <div className="space-y-1">
              <p className="font-medium text-sm md:text-base">{item.title}</p>
              <p className="text-sm text-muted-foreground">{item.description}</p>
            </div>
          </div>
        ))}
      </CardContent>
      <CardFooter className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">
          대화를 시작하면 온보딩은 자동으로 완료 처리됩니다.
        </p>
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
          {onSkip && (
            <Button
              className="w-full sm:w-auto"
              onClick={onSkip}
              variant="ghost"
            >
              나중에 보기
            </Button>
          )}
          <Button
            className="w-full sm:w-auto"
            disabled={isCompleting}
            onClick={onComplete}
          >
            {isCompleting ? "시작 준비 중..." : "지금 시작하기"}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
