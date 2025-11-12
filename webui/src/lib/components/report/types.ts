export interface ReportTemplate {
	id: string;
	category: string;
	title: string;
	description: string;
	tags: string[];
	metrics: Array<{
		label: string;
		value: string;
		accent?: 'primary' | 'secondary' | 'accent';
	}>;
	previewHtml: string;
}

