export type TestStatus =
    | "pass"
    | "fail"
    | "skip"
    | "error";

// export type Platform =
//     | "github"
//     | "gitlab";

export const Platforms = [
    "github",
    "gitlab"
] as const;
export type Platform = typeof Platforms[number];

export interface Repo {
    id: number;
    full_name: string;
    platform: Platform;
    default_branch: string;
    url: string;
    last_synced_at: string | null;
    created_at: string;
}

export interface PipelineRun {
    id: number;
    repo_id: number;
    external_id: number;
    commit_hash: string;
    commit_message: string | null;
    branch: string | null;
    status: string;
    conclusion: string | null;
    total_duration_s: number | null;
    started_at: string | null;
    completed_at: string | null;
    compared_to_prev_pct: number | null;
    created_at: string;
}

export interface PipelineRunDetail extends PipelineRun {
    jobs: JobTiming[];
    tests: TestRun[];
}

export interface JobTiming {
    id: number;
    run_id: number;
    external_id: number;
    job_name: string;
    status: string;
    duration_s: number | null;
    started_at: string | null;
    completed_at: string | null;
    compared_to_prev_pct: number | null;
}

export interface TestRun {
    id: number;
    run_id: number;
    test_name: string;
    status: TestStatus;
    duration_ms: number | null;
    avg_duration_ms: number | null;
    diff_from_avg_pct: number | null;
    color: string;
    created_at: string;
}

export interface TestHistoryPoint {
    commit_hash: string;
    commit_message: string | null;
    status: TestStatus;
    duration_ms: number | null;
    avg_duration_ms: number | null;
    diff_from_avg_pct: number | null;
    color: string;
    timestamp: string | null;
}

export interface Insight {
    level: string;
    icon: string;
    title: string;
    detail: string;
    commit_hash: string | null;
    test_name: string | null;
}

export interface TrendPoint {
    commit_hash: string;
    timestamp: string | null;
    total_duration_s: number | null;
    status: string;
    test_count: number;
    test_pass_count: number;
    test_fail_count: number;
}

export interface SyncStatus {
    repo_id: number;
    runs_synced: number;
    jobs_synced: number;
    tests_parsed: number;
    message: string;
}

export interface Message {
    role: "user" | "assistant";
    content: string;
    error?: boolean;
};

export interface Session {
    id: number | null;
    session_name: string;
    created_at: string;
    updated_at: string;
    project?: Project | null;
    pipeline?: Pipeline | null;
};

export interface AuthContextType {
    username: string | null;
    loading: boolean | null;
    isGuest: boolean;
    login: (username: string) => void;
    loginAsGuest: () => void;
    logout: () => void;
};

// Passed as router `state` when redirecting to /login, so Login knows where
// to send the person back to afterwards and whether "Continue as Guest"
// should be offered for that particular destination.
export interface LoginRedirectState {
    from?: { pathname: string };
    allowGuest?: boolean;
};

export interface Project {
    id: number;
    user_id: number;
    project_name: string;
    branch:string;
    repo_url: string;
    platform: Platform;
    created_at: string;
    updated_at: string;
}

export interface Pipeline {
    id: number;
    pipeline_id?: number;
    name: string;
    commit_author: string;
    commit_hash?: string;
    branch: string;
    path: string;
    content: string;
    is_active: boolean;
    created_at: Date;
    updated_at: Date;
    commited_at: Date;
    is_generated_by_wizard: boolean;
}

export interface Job {
    id: string;
    display_index?: number;
    stage?: string | null;
    needs?: string[];
    content: string;
}

export interface JobReview {
    pipeline_id: number;
    platform: string;
    jobs: Job[];
    content: string;
    valid: boolean;
    errors: string[];
    warnings: string[];
    ai_warnings: string[];
    ai_review: {
        available: boolean,
        model: string,
        error: string
    }
    commited: boolean;
}