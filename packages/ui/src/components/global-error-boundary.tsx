import { Component, ReactNode } from 'react';
import { captureError } from '@neo/utils';
import { Button } from './button';

export interface GlobalErrorBoundaryProps {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class GlobalErrorBoundary extends Component<
  GlobalErrorBoundaryProps,
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    if (typeof window !== 'undefined') {
      captureError(error, { route: window.location.pathname });
    }
  }

  private handleRetry = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div className="p-4 text-center space-y-4">
          <p>Something went wrong.</p>
          <Button onClick={this.handleRetry}>Retry</Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default GlobalErrorBoundary;
