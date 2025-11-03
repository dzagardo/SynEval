#!/usr/bin/env python3

import argparse
import pandas as pd
import json
import numpy as np
from pathlib import Path
from typing import Dict, List
from fidelity import FidelityEvaluator
from utility import UtilityEvaluator
from diversity import DiversityEvaluator
from privacy import PrivacyEvaluator
import logging


class SingleDatasetEvaluator:
    def __init__(self, data: pd.DataFrame, metadata: Dict):
        """
        单数据集评估器，用于筛选合适的训练集
        
        Args:
            data: 要评估的数据集
            metadata: 数据集的元数据信息
        """
        self.data = data
        self.metadata = metadata
        self.logger = logging.getLogger(__name__)
        
        # 初始化评估器为 None - 需要时创建
        self._fidelity_evaluator = None
        self._diversity_evaluator = None
        self._privacy_evaluator = None
        self._utility_evaluator = None

    def evaluate_fidelity(self, selected_metrics: List[str] = None) -> Dict:
        """评估数据保真度（数据质量）"""
        if self._fidelity_evaluator is None:
            # 对于单数据集评估，使用相同的数据作为原始数据
            self._fidelity_evaluator = FidelityEvaluator(self.data, self.data, self.metadata, selected_metrics)
        else:
            # 更新选定的指标
            self._fidelity_evaluator.selected_metrics = selected_metrics if selected_metrics else self._fidelity_evaluator.available_metrics
        return self._fidelity_evaluator.evaluate()

    def evaluate_utility(self, input_columns: List[str], output_columns: List[str], selected_metrics: List[str] = None) -> Dict:
        """评估数据实用性（机器学习任务性能）"""
        # 每次创建新的实用评估器，因为它需要输入/输出列
        utility_evaluator = UtilityEvaluator(
            self.data,
            self.data,  # 使用相同数据作为原始数据
            self.metadata,
            input_columns=input_columns,
            output_columns=output_columns,
            selected_metrics=selected_metrics
        )
        return utility_evaluator.evaluate()

    def evaluate_diversity(self, selected_metrics: List[str] = None) -> Dict:
        """评估数据多样性"""
        if self._diversity_evaluator is None:
            self._diversity_evaluator = DiversityEvaluator(self.data, self.data, self.metadata, selected_metrics=selected_metrics)
        else:
            # 更新选定的指标
            self._diversity_evaluator.selected_metrics = selected_metrics if selected_metrics else self._diversity_evaluator.available_metrics
        return self._diversity_evaluator.evaluate()

    def evaluate_privacy(self, selected_metrics: List[str] = None) -> Dict:
        """评估数据隐私性"""
        if self._privacy_evaluator is None:
            self._privacy_evaluator = PrivacyEvaluator(self.data, self.data, self.metadata, selected_metrics)
        else:
            # 更新选定的指标
            self._privacy_evaluator.selected_metrics = selected_metrics if selected_metrics else self._privacy_evaluator.available_metrics
        return self._privacy_evaluator.evaluate()

    def evaluate_correlation(self, correlation_types, **kwargs):
        """评估跨模态相关性"""
        if self._utility_evaluator is None:
            self._utility_evaluator = UtilityEvaluator(self.data, self.data, self.metadata, input_columns=[], output_columns=[])
        return self._utility_evaluator.evaluate_correlation(correlation_types, **kwargs)

    def get_dataset_summary(self) -> Dict:
        """获取数据集基本统计信息"""
        summary = {
            'dataset_info': {
                'shape': self.data.shape,
                'columns': list(self.data.columns),
                'memory_usage_mb': self.data.memory_usage(deep=True).sum() / 1024 / 1024,
                'missing_values': self.data.isnull().sum().to_dict(),
                'duplicate_rows': self.data.duplicated().sum()
            },
            'column_types': {},
            'basic_statistics': {}
        }
        
        # 按列类型分组统计
        for col, info in self.metadata.get('columns', {}).items():
            if col in self.data.columns:
                col_type = info.get('sdtype', 'unknown')
                summary['column_types'][col] = col_type
                
                if col_type == 'numerical':
                    summary['basic_statistics'][col] = {
                        'mean': self.data[col].mean(),
                        'std': self.data[col].std(),
                        'min': self.data[col].min(),
                        'max': self.data[col].max(),
                        'median': self.data[col].median()
                    }
                elif col_type == 'categorical':
                    summary['basic_statistics'][col] = {
                        'unique_values': self.data[col].nunique(),
                        'most_common': self.data[col].value_counts().head(5).to_dict()
                    }
                elif col_type == 'text':
                    text_lengths = self.data[col].str.len()
                    summary['basic_statistics'][col] = {
                        'avg_length': text_lengths.mean(),
                        'min_length': text_lengths.min(),
                        'max_length': text_lengths.max(),
                        'empty_texts': (self.data[col] == '').sum()
                    }
        
        return summary


def parse_args():
    parser = argparse.ArgumentParser(description='单数据集评估框架 - 用于筛选合适的训练集')

    parser.add_argument('--data', required=True, help='要评估的数据集CSV文件路径')
    parser.add_argument('--metadata', required=True, help='元数据JSON文件路径')

    parser.add_argument('--dimensions', nargs='+', 
                        choices=['fidelity', 'utility', 'diversity', 'privacy', 'summary'],
                        default=['summary', 'fidelity', 'diversity', 'privacy'],
                        help='要运行的评估维度 (默认: summary, fidelity, diversity, privacy)')
    parser.add_argument('--dimension', nargs='+', 
                        choices=['fidelity', 'utility', 'diversity', 'privacy', 'summary'],
                        help='--dimensions 的别名 (单数形式)')

    parser.add_argument('--utility-input', nargs='+', help='实用评估的输入列')
    parser.add_argument('--utility-output', nargs='+', help='实用评估的输出列')

    # 保真度指标选择
    parser.add_argument('--fidelity-metrics', nargs='+',
                        choices=['diagnostic', 'quality', 'text', 'numerical_statistics'],
                        help='要运行的特定保真度指标 (默认: 全部)')
    
    # 多样性指标选择
    parser.add_argument('--diversity-metrics', nargs='+',
                        choices=['tabular_diversity', 'text_diversity'],
                        help='要运行的特定多样性指标 (默认: 全部)')
    
    # 实用性指标选择
    parser.add_argument('--utility-metrics', nargs='+',
                        choices=['tstr_accuracy', 'correlation_analysis'],
                        help='要运行的特定实用性指标 (默认: 全部)')
    
    # 隐私指标选择
    parser.add_argument('--privacy-metrics', nargs='+',
                        choices=['exact_matches', 'membership_inference', 'tabular_privacy', 'text_privacy', 'anonymeter'],
                        help='要运行的特定隐私指标 (默认: 全部)')
    
    # 相关性指标（向后兼容）
    parser.add_argument('--correlation', nargs='+',
                        choices=['sentiment_rating', 'keyword_category', 'numeric_length', 'semantic_tabular', 'pii_text_leakage'],
                        help='要运行的跨模态相关性指标 (遗留，使用 --utility-metrics correlation_analysis)')
    parser.add_argument('--correlation-text-col', default='review', help='相关性分析的文本列')
    parser.add_argument('--correlation-rating-col', default='rating', help='情感相关性的评分列')
    parser.add_argument('--correlation-category-col', default='category', help='关键词相关性的类别列')
    parser.add_argument('--correlation-numeric-col', default='price', help='长度相关性的数值列')
    parser.add_argument('--correlation-pii-col', default='user_id', help='泄漏相关性的PII列')
    parser.add_argument('--correlation-top-n', type=int, default=50, help='关键词-类别相关性的前N个关键词')

    parser.add_argument('--output', default='./single_dataset_evaluation.json', help='保存评估结果的路径')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='设置日志级别')
    parser.add_argument('--plot', action='store_true', help='为所有评估指标生成图表并保存到 ./plots 目录')
    
    return parser

def main():
    parser = parse_args()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # 加载数据
    logger.info(f"正在加载数据集: {args.data}")
    data = pd.read_csv(args.data)

    logger.info(f"正在加载元数据: {args.metadata}")
    with open(args.metadata, 'r') as f:
        metadata = json.load(f)

    # 删除未在元数据中定义的 _id
    metadata_columns = metadata.get("columns", {})
    if '_id' in data.columns and '_id' not in metadata_columns:
        logger.warning("在数据中发现 '_id' 列但元数据中未定义 — 正在删除")
        data.drop(columns=['_id'], inplace=True)

    # 处理 --dimensions 和 --dimension 参数
    dimensions = args.dimensions
    if args.dimension:
        dimensions = args.dimension
    
    # 验证实用参数（如果请求）
    if 'utility' in dimensions:
        if not args.utility_input or not args.utility_output:
            parser.error("实用评估需要 --utility-input 和 --utility-output 参数")

    # 运行评估
    evaluator = SingleDatasetEvaluator(data, metadata)
    results = {}

    if 'summary' in dimensions:
        logger.info("正在生成数据集摘要...")
        results['summary'] = evaluator.get_dataset_summary()

    if 'fidelity' in dimensions:
        logger.info("正在运行保真度评估...")
        results['fidelity'] = evaluator.evaluate_fidelity(selected_metrics=args.fidelity_metrics)

    if 'utility' in dimensions:
        logger.info("正在运行实用性评估...")
        results['utility'] = evaluator.evaluate_utility(
            input_columns=args.utility_input,
            output_columns=args.utility_output,
            selected_metrics=args.utility_metrics
        )

    if 'diversity' in dimensions:
        logger.info("正在运行多样性评估...")
        try:
            results['diversity'] = evaluator.evaluate_diversity(selected_metrics=args.diversity_metrics)
            logger.info("多样性评估成功完成")
        except Exception as e:
            logger.error(f"多样性评估出错: {str(e)}")
            results['diversity'] = {
                'error': str(e),
                'tabular_diversity': {},
                'text_diversity': {}
            }

    if 'privacy' in dimensions:
        logger.info("正在运行隐私评估...")
        try:
            results['privacy'] = evaluator.evaluate_privacy(selected_metrics=args.privacy_metrics)
            logger.info("隐私评估成功完成")
        except Exception as e:
            logger.error(f"隐私评估出错: {str(e)}")
            results['privacy'] = {
                'error': str(e),
                'membership_inference': {},
                'exact_matches': {}
            }

    if args.correlation:
        logger.info(f"正在运行相关性评估: {args.correlation}")
        correlation_kwargs = dict(
            text_col=args.correlation_text_col,
            rating_col=args.correlation_rating_col,
            category_col=args.correlation_category_col,
            numeric_col=args.correlation_numeric_col,
            pii_col=args.correlation_pii_col,
            top_n=args.correlation_top_n
        )
        results['correlation'] = evaluator.evaluate_correlation(args.correlation, **correlation_kwargs)

    # 在保存前转换任何不可序列化的值（例如 NaN）
    def safe_json(obj):
        try:
            return json.loads(json.dumps(obj, default=str))
        except Exception as e:
            logger.error(f"序列化结果时出错: {str(e)}")
            return {"error": "序列化结果失败", "original_error": str(e)}

    # 保存结果
    logger.info(f"正在保存结果到 {args.output}")
    try:
        safe_results = safe_json(results)
        with open(args.output, 'w') as f:
            json.dump(safe_results, f, indent=2)
        logger.info(f"结果已成功保存到 {args.output}")
    except Exception as e:
        logger.error(f"保存结果到 {args.output} 时出错: {str(e)}")
        # 尝试保存到备份文件
        backup_file = f"{args.output}.backup"
        try:
            with open(backup_file, 'w') as f:
                json.dump(safe_results, f, indent=2)
            logger.info(f"结果已保存到备份文件: {backup_file}")
        except Exception as backup_e:
            logger.error(f"保存备份文件失败: {str(backup_e)}")

    # 显示结果摘要
    print("\n📊 单数据集评估结果摘要")
    print("=" * 50)
    display_results_summary(results)

    # 如果请求则生成图表
    if getattr(args, 'plot', False):
        logger.info("正在为评估结果生成图表...")
        try:
            from plotting import SynEvalPlotter
            plotter = SynEvalPlotter(output_dir='./plots')
            plotter.plot_all_results(results, save_plots=True)
            logger.info("图表已保存到 ./plots 目录")
        except ImportError as e:
            logger.warning(f"绘图模块不可用: {str(e)}")
        except Exception as e:
            logger.error(f"生成图表时出错: {str(e)}")

    logger.info("评估完成!")
    return results

def display_results_summary(results: Dict):
    """显示评估结果摘要"""
    
    for dimension, dimension_results in results.items():
        print(f"\n🔍 {dimension.upper()} 评估")
        print("-" * 30)
        
        if dimension == 'summary':
            if 'dataset_info' in dimension_results:
                info = dimension_results['dataset_info']
                print(f"数据集形状: {info.get('shape', 'N/A')}")
                print(f"内存使用: {info.get('memory_usage_mb', 'N/A'):.2f} MB")
                print(f"重复行数: {info.get('duplicate_rows', 'N/A')}")
                print(f"列数: {len(info.get('columns', []))}")
                
                missing_values = info.get('missing_values', {})
                total_missing = sum(missing_values.values())
                if total_missing > 0:
                    print(f"总缺失值: {total_missing}")
                    # 显示缺失值最多的前3列
                    sorted_missing = sorted(missing_values.items(), key=lambda x: x[1], reverse=True)[:3]
                    for col, count in sorted_missing:
                        if count > 0:
                            print(f"  {col}: {count}")
        
        elif dimension == 'fidelity':
            if 'diagnostic' in dimension_results and dimension_results['diagnostic']:
                diag = dimension_results['diagnostic']
                print(f"数据有效性: {diag.get('Data Validity', 'N/A')}")
                print(f"数据结构: {diag.get('Data Structure', 'N/A')}")
                print(f"总体评分: {diag.get('Overall', {}).get('score', 'N/A')}")
            
            if 'numerical_statistics' in dimension_results:
                num_stats = dimension_results['numerical_statistics']
                if num_stats:
                    fidelity_scores = [col_data.get('overall_fidelity_score', 0) 
                                     for col_data in num_stats.values() 
                                     if isinstance(col_data, dict) and 'overall_fidelity_score' in col_data]
                    if fidelity_scores:
                        avg_fidelity = sum(fidelity_scores) / len(fidelity_scores)
                        if isinstance(avg_fidelity, (int, float)):
                            print(f"平均数值保真度: {avg_fidelity:.3f}")
                        else:
                            print(f"平均数值保真度: {avg_fidelity}")
        
        elif dimension == 'utility':
            if 'tstr_accuracy' in dimension_results:
                tstr_results = dimension_results['tstr_accuracy']
                if 'real_data_model' in tstr_results and 'synthetic_data_model' in tstr_results:
                    real_acc = tstr_results['real_data_model'].get('accuracy', 0)
                    syn_acc = tstr_results['synthetic_data_model'].get('accuracy', 0)
                    
                    real_acc_formatted = f"{real_acc:.3f}" if isinstance(real_acc, (int, float)) else str(real_acc)
                    syn_acc_formatted = f"{syn_acc:.3f}" if isinstance(syn_acc, (int, float)) else str(syn_acc)
                    
                    print(f"任务类型: {tstr_results.get('task_type', 'N/A')}")
                    print(f"训练大小: {tstr_results.get('training_size', 'N/A')}")
                    print(f"测试大小: {tstr_results.get('test_size', 'N/A')}")
                    print(f"模型准确率: {syn_acc_formatted}")
        
        elif dimension == 'diversity':
            if 'tabular_diversity' in dimension_results:
                tab = dimension_results['tabular_diversity']
                
                if 'coverage' in tab and tab['coverage']:
                    avg_coverage = sum(tab['coverage'].values()) / len(tab['coverage'])
                    if isinstance(avg_coverage, (int, float)):
                        print(f"平均表格覆盖率: {avg_coverage:.1f}%")
                    else:
                        print(f"平均表格覆盖率: {avg_coverage}%")
                
                if 'uniqueness' in tab and tab['uniqueness']:
                    if 'duplicate_ratio' in tab['uniqueness']:
                        dup_ratio = tab['uniqueness']['duplicate_ratio']
                        if isinstance(dup_ratio, (int, float)):
                            print(f"重复比例: {dup_ratio:.3f}")
                        else:
                            print(f"重复比例: {dup_ratio}")
                
                if 'entropy_metrics' in tab and tab['entropy_metrics']:
                    if 'dataset_entropy' in tab['entropy_metrics']:
                        entropy_data = tab['entropy_metrics']['dataset_entropy']
                        if 'entropy_ratio' in entropy_data:
                            entropy_ratio = entropy_data['entropy_ratio']
                            if isinstance(entropy_ratio, (int, float)):
                                print(f"熵比例: {entropy_ratio:.3f}")
                            else:
                                print(f"熵比例: {entropy_ratio}")
            
            if 'text_diversity' in dimension_results:
                text_div = dimension_results['text_diversity']
                if 'synthetic' in text_div and text_div['synthetic']:
                    first_col = next(iter(text_div['synthetic']), None)
                    if first_col:
                        col_results = text_div['synthetic'][first_col]
                        
                        if 'lexical_diversity' in col_results:
                            lex_div = col_results['lexical_diversity']
                            if '1-gram' in lex_div and 'unique_ratio' in lex_div['1-gram']:
                                unique_ratio = lex_div['1-gram']['unique_ratio']
                                if isinstance(unique_ratio, (int, float)):
                                    print(f"文本词汇多样性: {unique_ratio:.3f}")
                                else:
                                    print(f"文本词汇多样性: {unique_ratio}")
                        
                        if 'semantic_diversity' in col_results:
                            sem_div = col_results['semantic_diversity']
                            if 'distinct_ratio' in sem_div:
                                distinct_ratio = sem_div['distinct_ratio']
                                if isinstance(distinct_ratio, (int, float)):
                                    print(f"文本语义多样性: {distinct_ratio:.3f}")
                                else:
                                    print(f"文本语义多样性: {distinct_ratio}")
        
        elif dimension == 'privacy':
            if 'membership_inference' in dimension_results:
                distinguishability = dimension_results['membership_inference']
                auc_value = distinguishability.get('distinguishability_auc', None)
                fidelity_score = distinguishability.get('fidelity_score', None)

                if isinstance(auc_value, (int, float)):
                    print(f"合成-真实可区分度 AUC: {auc_value:.3f}")
                else:
                    print("合成-真实可区分度 AUC: N/A")

                if isinstance(fidelity_score, (int, float)):
                    print(f"AUC 推导的相似度得分(1-AUC): {fidelity_score:.3f}")

            if 'exact_matches' in dimension_results:
                exact = dimension_results['exact_matches']
                print(f"精确匹配风险: {exact.get('risk_level', 'N/A')}")
                
                exact_percentage = exact.get('exact_match_percentage', None)
                if isinstance(exact_percentage, (int, float)):
                    print(f"精确匹配百分比: {exact_percentage:.2f}%")
            
            if 'anonymeter' in dimension_results:
                anonymeter = dimension_results['anonymeter']
                if 'overall_risk' in anonymeter:
                    overall_risk = anonymeter['overall_risk']
                    risk_score = overall_risk.get('risk_score', None)
                    risk_level = overall_risk.get('risk_level', 'N/A')
                    if isinstance(risk_score, (int, float)):
                        print(f"Anonymeter 总体风险评分: {risk_score:.3f}")
                    print(f"Anonymeter 风险等级: {risk_level}")

        if 'correlation' in results:
            print(f"\n🔗 跨模态相关性")
            print("-" * 30)
            for k, v in results['correlation'].items():
                print(f"{k}: {v}")

if __name__ == "__main__":
    main() 
