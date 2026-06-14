/**
 * ErrorBoundary — 렌더 중 예외로 화면이 하얗게(white screen) 죽는 것을 막는다.
 * 데모 도구는 어떤 오류에서도 "무엇이 잘못됐는지"를 보여야 한다(시연 중단 방지).
 * 잡은 오류는 콘솔에 남기고, 화면에는 메시지·스택과 복구 버튼을 표시한다.
 */
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
  componentStack: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, componentStack: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // 콘솔에 전체 오류·컴포넌트 스택 기록 (진단용)
    console.error("[ErrorBoundary] 렌더 오류:", error, info.componentStack);
    this.setState({ componentStack: info.componentStack ?? null });
  }

  private reset = () => this.setState({ error: null, componentStack: null });

  render(): ReactNode {
    const { error, componentStack } = this.state;
    if (!error) return this.props.children;

    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          background: "var(--color-neutral-10, #fbf9f8)",
          color: "var(--color-neutral-90, #161513)",
          fontFamily: "var(--font-sans, system-ui, sans-serif)",
        }}
      >
        <div
          style={{
            maxWidth: 720,
            width: "100%",
            background: "var(--color-neutral-0, #fff)",
            border: "1px solid var(--color-neutral-30, #e4e1dd)",
            borderTop: "3px solid var(--color-danger, #c7402e)",
            borderRadius: 8,
            padding: 24,
            boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
          }}
        >
          <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
            화면을 그리는 중 오류가 발생했습니다
          </h1>
          <p style={{ fontSize: 14, color: "var(--color-neutral-70, #4a4640)", marginBottom: 12 }}>
            데이터를 확인한 뒤 다시 시도하세요. 아래 메시지를 알려주시면 원인을 빠르게 찾을 수 있습니다.
          </p>
          <pre
            style={{
              fontFamily: "var(--font-mono, ui-monospace, monospace)",
              fontSize: 12,
              background: "var(--color-code-bg, #25221f)",
              color: "#e8e6e3",
              padding: 12,
              borderRadius: 6,
              overflow: "auto",
              maxHeight: 280,
              whiteSpace: "pre-wrap",
            }}
          >
            {error.name}: {error.message}
            {componentStack ? `\n${componentStack}` : ""}
          </pre>
          <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
            <button
              onClick={this.reset}
              style={{
                height: 36,
                padding: "0 16px",
                borderRadius: 6,
                border: "none",
                background: "var(--color-action-primary, #161513)",
                color: "#fff",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              다시 시도
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                height: 36,
                padding: "0 16px",
                borderRadius: 6,
                border: "1px solid var(--color-neutral-40, #cfcbc6)",
                background: "#fff",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              새로고침
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
