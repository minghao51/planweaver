import React, { useMemo } from 'react';
import ReactFlow, {
    Node,
    Edge,
    Background,
    Controls,
    MiniMap,
    Handle,
    Position,
    NodeProps,
    MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ExecutionStep } from '../types';
import { cn } from '../utils';

interface FlowCanvasProps {
    steps: ExecutionStep[];
}

const StepNode = ({ data }: NodeProps<ExecutionStep>) => {
    const statusColors = {
        PENDING: 'bg-surface-alt border-border text-text-muted',
        IN_PROGRESS: 'bg-primary/20 border-primary text-primary animate-pulse',
        COMPLETED: 'bg-success/20 border-success text-success',
        FAILED: 'bg-danger/20 border-danger text-danger',
    };

    const status = data.status as keyof typeof statusColors;

    return (
        <div className={cn(
            "px-4 py-3 rounded-xl border shadow-lg min-w-[200px] transition-all duration-300",
            statusColors[status] || statusColors.PENDING
        )}>
            <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-primary" />
            <div className="flex flex-col gap-1">
                <div className="text-[10px] font-bold uppercase tracking-wider opacity-60">
                    Step {data.step_id}
                </div>
                <div className="text-sm font-medium leading-tight line-clamp-2">
                    {data.task}
                </div>
                <div className="mt-2 text-[10px] bg-black/20 self-start px-2 py-0.5 rounded-full">
                    {data.assigned_model?.split('/').pop() ?? 'unknown'}
                </div>
            </div>
            <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-primary" />
        </div>
    );
};

const nodeTypes = {
    step: StepNode,
};

export const FlowCanvas: React.FC<FlowCanvasProps> = ({ steps = [] }) => {
    const { nodes, edges } = useMemo(() => {
        const nodes: Node[] = [];
        const edges: Edge[] = [];

        steps.forEach((step, index) => {
            nodes.push({
                id: step.step_id.toString(),
                type: 'step',
                data: step,
                position: { x: 250, y: index * 150 },
            });

            step.dependencies?.forEach((depId) => {
                edges.push({
                    id: `e${depId}-${step.step_id}`,
                    source: depId.toString(),
                    target: step.step_id.toString(),
                    animated: step.status === 'IN_PROGRESS',
                    style: { stroke: step.status === 'COMPLETED' ? '#22c55e' : '#38bdf8' },
                    markerEnd: {
                        type: MarkerType.ArrowClosed,
                        color: step.status === 'COMPLETED' ? '#22c55e' : '#38bdf8',
                    },
                });
            });
        });

        return { nodes, edges };
    }, [steps]);

    return (
        <div className="w-full h-[600px] bg-bg rounded-2xl border border-border overflow-hidden">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                fitView
                className="bg-bg"
            >
                <Background color="#123048" gap={20} />
                <Controls />
                <MiniMap
                    nodeColor={(n) => {
                        if (n.data?.status === 'COMPLETED') return '#22c55e';
                        if (n.data?.status === 'IN_PROGRESS') return '#38bdf8';
                        return '#26455f';
                    }}
                    style={{ backgroundColor: '#0a1a28' }}
                />
            </ReactFlow>
        </div>
    );
};
